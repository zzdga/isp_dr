#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2015 Mikael Sandström <oravirt@gmail.com>
# Copyright: (c) 2021, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: oracle_parameter
short_description: Manage parameters in an Oracle database
description:
    - This module manages parameters in an Oracle database.
    - Parameters value comparison is case sensitive, module wise.
      To avoid Ansible I(changed) state, check the case of the value.
    - Hidden parameters can be changed using sysdba privileges.
version_added: "0.8.0"
author:
    - Mikael Sandström (@oravirt)
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
    name:
        description:
            - Name of the parameter to change.
        required: true
        type: str
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
    scope:
        description:
            - Lets you specify when the change takes effect.
            - If I(scope=memory), takes effect immediatly but doesn't persist.
            - If I(scope=spfile), takes effect after next shutdown and persists.
            - If I(scope=both), takes effect immediatly and persists.
        default: both
        type: str
        choices: ['both', 'memory', 'spfile']
    service_name:
        description:
            - Specify the service name of the database you want to access.
        required: true
        type: str
    sid:
        description:
            - Specify the SID of the instance where the value will take effect.
        default: '*'
        type: str
    state:
        description:
            - The intended state of the parameter.
            - I(state=present) is synonymous of I(state=defined).
            - I(state=absent) is synonymous of I(state=default).
        default: defined
        type: str
        choices: ['absent', 'default', 'defined', 'present']
    username:
        description:
            - Set the login to use to connect the database server.
            - Must not be set if using Oracle wallet.
        type: str
        aliases:
            - user
    value:
        description:
            - The value of the parameter.
            - I(value) is mandatory is I(state=defined).
        required: false
        type: str
        aliases: ['parameter']
requirements:
    - Python module cx_Oracle
    - Oracle basic tools.
notes:
    - Check mode is supported.
    - Diff mode is supported.
'''

EXAMPLES = '''
- name: Set the value of db_recovery_file_dest
  oracle_parameter:
    hostname: remote-db-server
    service_name: orcl
    username: system
    password: manager
    name: db_recovery_file_dest
    value: '+FRA'
    state: defined
    scope: both
    sid: '*'

- name: Set the value of db_recovery_file_dest_size
  oracle_parameter:
    hostname: remote-db-server
    service_name: orcl
    username: system
    password: manager
    name: db_recovery_file_dest_size
    value: 100G
    state: defined
    scope: both

- name: Reset the value of open_cursors
  oracle_parameter:
    hostname: remote-db-server
    service_name: orcl
    username: system
    password: manager
    name: open_cursors
    state: default
    scope: spfile
'''

RETURN = '''
ddls:
    description: Ordered list of DDL requests executed during module execution.
    returned: always
    type: list
    elements: str
'''

from ansible.module_utils.basic import AnsibleModule, re
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_db import OraDB

MEMORY_SCOPE = 'memory'
SPFILE_SCOPE = 'spfile'
ALL_SCOPES = [MEMORY_SCOPE, SPFILE_SCOPE]


def ensure_defined(name, value, scopes, sid, mode):
    """Ensure the parameter has the correct value, scope wise."""
    changed = False

    for scope in ALL_SCOPES:
        # Modify value by scope, for better granularity on "changed" value.
        if scope in scopes and existing_parameter[scope]['value'] != value:
            # Oracle doesn't accept string for all parameters.
            o_value = value if re.match(r'(\w|\d)+', value) else "'%s'" % value
            ora_db.execute_ddl('alter system set "%s" = %s scope=%s sid=\'%s\'' % (name, o_value, scope, sid))
            changed = True

    if changed:
        _set_diff('after', name, mode)
        module.exit_json(msg='Parameter %s changed.' % name, changed=True, ddls=ora_db.ddls, diff=diff)
    else:
        module.exit_json(msg='Parameter %s already to specified value.' % name, changed=False)


def ensure_default(name, scopes, sid, mode):
    """Ensure the parameter has default value, scope wise."""
    changed = False

    for scope in ALL_SCOPES:
        # Modify value by scope, for better granularity on "changed" value.
        if scope in scopes and existing_parameter[scope]['is_modified']:
            ora_db.execute_ddl('alter system reset "%s" scope=%s sid=\'%s\'' % (name, scope, sid))
            changed = True

    if changed:
        _set_diff('after', name, mode)
        module.exit_json(msg='Parameter %s returned to its default value.' % name, changed=True, ddls=ora_db.ddls,
                         diff=diff)
    else:
        module.exit_json(msg='Parameter %s already to default value.' % name, changed=False)


def _set_diff(time, name, mode):
    """Fill the diff hash with a period of time, before or after."""
    parameter = get_existing_parameter(name, mode)
    diff[time]['name'] = parameter['name']
    diff[time]['sid'] = parameter['sid']
    for scope in ALL_SCOPES:
        diff[time][scope] = {}
        diff[time][scope]['value'] = parameter[scope]['value'] if parameter[scope] else None
        diff[time][scope]['is_modified'] = parameter[scope]['is_modified'] if parameter[scope] else None


def get_existing_parameter(name, mode):
    """Get existing value of the parameter in memory and spfile."""
    sql = "select name, value, '%s' as scope, null as sid, ismodified from v$parameter where name = :name" \
          " union all " \
          "select name, value, '%s', sid, isspecified from v$spparameter where name = :name" % (
              MEMORY_SCOPE, SPFILE_SCOPE)
    if name.startswith('_') and mode == 'sysdba':
        sql += " union all " \
               "select p.ksppinm, v.ksppstvl, 'hidden', '*', v.ksppstdf" \
               "  from x$ksppi p, x$ksppcv v" \
               " where p.indx = v.indx and p.ksppinm = :name"

    rows = ora_db.execute_select(sql, {'name': name})
    if rows:
        result = {'name': name, MEMORY_SCOPE: {}, SPFILE_SCOPE: {}}
        for row in rows:
            value = row[1]
            scope = row[2]
            if scope == 'hidden':
                if result[SPFILE_SCOPE]:
                    continue  # If a spfile parameter is already defined, don't override the value.
                else:
                    scope = SPFILE_SCOPE  # Hidden parameter is a spfile parameter.
            sid = row[3] if row[3] is not None else None  # It's meant to avoid override of previous value by None.
            is_modified = row[4] != 'FALSE'

            result[scope]['value'] = value
            result[scope]['is_modified'] = is_modified
            result['sid'] = sid
        return result
    else:
        return None


def main():
    global module
    global ora_db
    global existing_parameter
    global diff

    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type='str', default='localhost'),
            mode=dict(type='str', default='normal', choices=['normal', 'sysdba']),
            name=dict(type='str', required=True, aliases=['parameter']),
            oracle_home=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=True),
            port=dict(type='int', default=1521),
            scope=dict(type='str', default='both', choices=['both', MEMORY_SCOPE, SPFILE_SCOPE]),
            service_name=dict(type='str', required=True),
            sid=dict(type='str', default='*'),
            state=dict(type='str', default='defined', choices=['absent', 'default', 'defined', 'present']),
            username=dict(type='str', required=False, aliases=['user']),
            value=dict(type='str', required=False),
        ),
        required_together=[['username', 'password']],
        required_if=[['state', 'present', ['value']],
                     ['state', 'defined', ['value']], ],
        supports_check_mode=True,
    )

    mode = module.params['mode']
    name = module.params['name']
    scope = module.params['scope']
    sid = module.params['sid']
    state = module.params['state']
    value = module.params['value']

    # Transforming parameters
    if state == 'present':
        state = 'defined'
    elif state == 'absent':
        state = 'default'
    scopes = ALL_SCOPES if scope == 'both' else [scope]

    ora_db = OraDB(module)

    existing_parameter = get_existing_parameter(name, mode)
    if existing_parameter is None:
        module.fail_json(msg="Parameter %s doesn't exist or sysdba privileges needed." % name, changed=False)

    diff = {'before': {}, 'after': {}}
    _set_diff('before', name, mode)

    if state == 'defined':
        ensure_defined(name, value, scopes, sid, mode)
    else:
        ensure_default(name, scopes, sid, mode)


if __name__ == '__main__':
    main()
