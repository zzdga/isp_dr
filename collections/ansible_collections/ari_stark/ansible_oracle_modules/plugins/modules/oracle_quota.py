#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: oracle_quota
short_description: Manages Oracle quota for users.
description:
    - This module manages Oracle quota for users.
    - It can ensure a single quota is present/absent.
    - It can ensure a list of quotas matches the quotas in database.
    - It can ensure a user has no quota.
    - Username and tablespace name are case insensitive.
version_added: "1.2.0"
author:
    - Ari Stark (@ari-stark)
options:
    hostname:
        description:
            - Specify the host name or IP address of the database server computer.
        default: localhost
        type: str
    mode:
        description:
            - This option is the database administration privileges.
        default: normal
        type: str
        choices: ['normal', 'sysdba']
    oracle_home:
        description:
            - Define the directory into which all Oracle software is installed.
            - Define ORACLE_HOME environment variable if set.
        type: str
    password:
        description:
            - Set the password to use to connect the database server.
            - Must not be set if using Oracle wallet.
        type: str
    port:
        description:
            - Specify the listening port on the database server.
        default: 1521
        type: int
    schema_name:
        description:
            - Name of the user to manage.
        required: true
        type: str
        aliases:
            - name
    service_name:
        description:
            - Specify the service name of the database you want to access.
        required: true
        type: str
    size:
        description:
            - Specify the size of the quota.
        default: unlimited
        type: str
    state:
        description:
            - Specify the state of the quota.
            - If I(state=absent) and no I(tablespace) nor I(tablespaces) are defined, all quotas will be removed.
            - If I(state=absent) with I(tablespace) or I(tablespaces), quotas will be remove for these tablepaces.
        default: present
        type: str
        choices: ['absent', 'present']
    tablespace:
        description:
            - Specify the tablespace name where quota must be defined.
            - I(tablespace) and I(tablespaces) are mutually exclusive.
            - When defined, module ensures the defined quota is absent/present with defined size.
            - This value is case insensitive.
        required: false
        type: str
    tablespaces:
        description:
            - Specify the list of tablespaces names where quota must be defined.
            - I(tablespace) and I(tablespaces) are mutually exclusive.
            - When defined and I(state=present), modules ensures the quotas are defined exactly,
              removing or adding quotas.
            - When defined and I(state=absent), modules ensures the quotas are absent for these tablespaces.
            - Values are case insensitive.
        required: false
        type: list
        elements: str
    username:
        description:
            - Set the login to use to connect the database server.
            - Must not be set if using Oracle wallet.
        type: str
        aliases:
            - user
requirements:
    - Python module cx_Oracle
    - Oracle basic tools.
notes:
    - Check mode and diff mode are supported.
'''

EXAMPLES = '''
- name: define unlimited quota to user on a tablespace
  oracle_quota:
    service_name: "xepdb1"
    username: "sys"
    password: "manager"
    mode: "sysdba"
    schema_name: "foo_user"
    tablespace: "foo_ts"
    state: "present"

- name: define quota to user on a tablespace
  oracle_quota:
    service_name: "xepdb1"
    username: "sys"
    password: "manager"
    mode: "sysdba"
    schema_name: "foo_user"
    tablespace: "foo_ts"
    size: "5M"
    state: "present"

- name: ensure quota for a user are defined (add, remove or change quota)
  oracle_quota:
    service_name: "xepdb1"
    username: "sys"
    password: "manager"
    mode: "sysdba"
    schema_name: "foo_user"
    tablespaces:
      - "foo_ts"
      - "bar_ts"
    size: "5M"
    state: "present"

- name: ensure quota is absent for user on a tablespace
  oracle_quota:
    service_name: "xepdb1"
    username: "sys"
    password: "manager"
    mode: "sysdba"
    schema_name: "foo_user"
    tablespace: "foo_ts"
    state: "absent"

- name: ensure a user has no quota
  oracle_quota:
    service_name: "xepdb1"
    username: "sys"
    password: "manager"
    mode: "sysdba"
    schema_name: "foo_user"
    state: "absent"
'''

RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from copy import deepcopy
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_db import OraDB
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_object import Size


def get_existing_quota(schema_name):
    """Get existant quotas of a user."""
    data = ora_db.execute_select("select lower(tablespace_name), max_bytes"
                                 "  from dba_ts_quotas"
                                 " where username = upper(:username)", {'username': schema_name})
    quotas = []
    for row in data:
        tablespace = row[0]
        size = Size(row[1])
        if size.size == -1:
            size.unlimited = True

        quota = {'tablespace': tablespace, 'size': size}
        diff['before']['quotas'].append({'tablespace': tablespace, 'size': str(size)})
        diff['after'] = deepcopy(diff['before'])
        quotas.append(quota)

    return quotas


def ensure_present(schema_name, tablespace, size):
    """Ensure one specific quota is present for a user."""
    quotas = get_existing_quota(schema_name)
    existing_tablespace_quota = next((quota for quota in quotas if quota['tablespace'] == tablespace), None)

    if existing_tablespace_quota and existing_tablespace_quota['size'] == size:
        module.exit_json(msg="Quota is already defined.", changed=False, diff=diff)
    else:
        ora_db.execute_ddl('alter user %s quota %s on %s' % (schema_name, size, tablespace))

        if existing_tablespace_quota:
            quota_to_change = next(quota for quota in diff['after']['quotas'] if quota['tablespace'] == tablespace)
            quota_to_change['size'] = str(size)
        else:
            diff['after']['quotas'].append({'tablespace': tablespace, 'size': str(size)})
        module.exit_json(msg="Quota was changed.", changed=True, ddls=ora_db.ddls, diff=diff)


def ensure_same(schema_name, tablespaces, size):
    """Ensure quotas for a user are as described."""
    quotas = get_existing_quota(schema_name)
    tablespaces_with_quota = list(quota['tablespace'] for quota in quotas)
    tablespaces_without_quota = list(
        tablespace for tablespace in tablespaces if tablespace not in tablespaces_with_quota)
    has_changed = False

    # Add missing quotas
    for tablespace in tablespaces_without_quota:
        ora_db.execute_ddl('alter user %s quota %s on %s' % (schema_name, size, tablespace))
        diff['after']['quotas'].append({'tablespace': tablespace, 'size': str(size)})
        has_changed = True

    # Remove superfluous quotas
    superfluous_tablespaces = list(tablespace for tablespace in tablespaces_with_quota if tablespace not in tablespaces)
    for tablespace in superfluous_tablespaces:
        ora_db.execute_ddl('alter user %s quota 0 on %s' % (schema_name, tablespace))
        quota_to_remove = next(quota for quota in diff['after']['quotas'] if quota['tablespace'] == tablespace)
        diff['after']['quotas'].remove(quota_to_remove)
        has_changed = True

    # Change missized quotas
    for quota in quotas:
        if quota['tablespace'] in tablespaces and quota['size'] != size:
            ora_db.execute_ddl('alter user %s quota %s on %s' % (schema_name, size, quota['tablespace']))
            diff_quota = next(q for q in diff['after']['quotas'] if q['tablespace'] == quota['tablespace'])
            diff_quota['size'] = str(size)
            has_changed = True

    if has_changed:
        module.exit_json(msg="Quotas were changed.", changed=True, ddls=ora_db.ddls, diff=diff)
    else:
        module.exit_json(msg="Quotas were already defined.", changed=False, ddls=ora_db.ddls, diff=diff)


def ensure_absent(schema_name, tablespace):
    """Ensure one specific quota is absent for a user."""
    quotas = get_existing_quota(schema_name)
    existing_tablespace_quota = next((quota for quota in quotas if quota['tablespace'] == tablespace), None)

    if existing_tablespace_quota:
        ora_db.execute_ddl('alter user %s quota 0 on %s' % (schema_name, tablespace))

        quota_to_change = next(quota for quota in diff['after']['quotas'] if quota['tablespace'] == tablespace)
        diff['after']['quotas'].remove(quota_to_change)

        module.exit_json(msg="Quota was removed.", changed=True, ddls=ora_db.ddls, diff=diff)
    else:
        module.exit_json(msg="Quota was already absent.", changed=False, diff=diff)


def ensure_no_quota(schema_name):
    """Ensure a user has no quota."""
    quotas = get_existing_quota(schema_name)

    if len(quotas) == 0:
        module.exit_json(msg="User has already no quota.", changed=False, diff=diff)
    else:
        for quota in quotas:
            ora_db.execute_ddl('alter user %s quota 0 on %s' % (schema_name, quota['tablespace']))

        diff['after']['quotas'] = []
        module.exit_json(msg="Quotas were removed.", changed=True, ddls=ora_db.ddls, diff=diff)


def main():
    global module
    global ora_db
    global diff

    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str', default='localhost'),
            mode=dict(type='str', default='normal', choices=['normal', 'sysdba']),
            oracle_home=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=True),
            port=dict(type='int', default=1521),
            schema_name=dict(type='str', required=True, aliases=['name']),
            service_name=dict(type='str', required=True),
            size=dict(type='str', default='unlimited'),
            state=dict(type='str', default='present', choices=['absent', 'present']),
            tablespace=dict(type='str', required=False),
            tablespaces=dict(type='list', elements='str', required=False),
            username=dict(type='str', required=False, aliases=['user']),
        ),
        required_together=[['username', 'password']],
        mutually_exclusive=[['tablespace', 'tablespaces']],
        supports_check_mode=True,
    )

    schema_name = module.params['schema_name']
    size = Size(module.params['size'])
    state = module.params['state']
    tablespace = module.params['tablespace']
    tablespaces = module.params['tablespaces']

    # Transform data
    schema_name = schema_name.lower()
    tablespace = tablespace.lower() if tablespace else None
    tablespaces = [tablespace.lower() for tablespace in tablespaces] if tablespaces is not None else None

    ora_db = OraDB(module)
    diff = {'before': {'quotas': []},
            'after': {'quotas': []}}

    if state == 'present' and tablespace is not None:
        ensure_present(schema_name, tablespace, size)
    elif state == 'present' and tablespaces is not None:
        ensure_same(schema_name, tablespaces, size)
    elif state == 'present':
        module.fail_json(msg="one parameter is mandatory when state=='present': tablespace|tablespaces", changed=False)
    elif state == 'absent' and tablespace is None and tablespaces is None:
        ensure_no_quota(schema_name)
    elif state == 'absent':
        ensure_absent(schema_name, tablespace)


if __name__ == '__main__':
    main()
