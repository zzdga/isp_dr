#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2014 Mikael Sandström <oravirt@gmail.com>
# Copyright: (c) 2020, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: oracle_grant
short_description: Manage Oracle privileges (system privileges, role privileges and object privileges)
description:
    - This module manage Oracle privileges.
    - It can deal with system privileges, role privileges and object privileges
      (procedure, function, package, package body and directory).
    - "It has 3 possible states: I(present), I(absent) and I(identical).
      States I(present) and I(absent) ensure privileges are present or absent.
      State I(identical) replace privileges with the ones in parameter."
version_added: "0.8.0"
author:
    - Mikael Sandström (@oravirt)
    - Ari Stark (@ari-stark)
options:
    grantee:
        description:
            - The schema or role that should be changed.
        type: str
        required: True
        aliases: ['schema', 'role']
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
    objects_privileges:
        description:
            - A dictionary containing the objects privileges.
            - The key of the dictionary is the name of the object in the format I(owner.object_name).
            - The value of the dictionary is a list of privileges.
            - Object name and privileges are changed to upper case.
            - If owner of the object is not specified, the I(username) use to connect will be used as the default owner.
            - Examples of format can be found below.
        default: {}
        type: dict
        aliases: ['obj_privs']
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
    privileges:
        description:
            - A list containing the system and role privileges.
        default: []
        type: list
        elements: str
        aliases: ['system_privileges', 'role_privileges']
    service_name:
        description:
            - Specify the service name of the database you want to access.
        required: true
        type: str
    state:
        description:
            - Specify the state of the privileges.
            - If I(present), the privileges will be added if needed.
            - If I(absent), the privileges will be removed if neeed.
            - If I(identical), the privileges in options will replace the existent privileges.
        default: identical
        type: str
        choices: ['present', 'absent', 'identical']
    username:
        description:
            - Set the login to use to connect the database server.
            - Must not be set if using Oracle wallet.
        type: str
requirements:
    - Python module cx_Oracle
    - Oracle basic tools.
notes:
    - Check mode and diff mode are supported.
    - Changes made by @ari-stark broke previous module interface.
    - The way to use I(objects_privileges) change completely by using a dict instead of strings.
    - The I(directory_privileges) was removed to use I(objects_privileges).
    - The I(state) and I(grants_mode) options were merged in I(state) option.
    - The I(schema) and I(role) options were merged in I(grantee) option.
'''

EXAMPLES = '''
- name: Set privileges to a user (removing existent privileges not in the list)
  oracle_grant:
    service_name: "xepdb1"
    username: "sys"
    password: "password"
    mode: "sysdba"
    grantee: "foo"
    privileges:
        - "create session"
        - "create table"
    objects_privileges:
        dbms_random:
            - "execute"
        my_directory:
            - "read"
            - "write"
            - "execute"

- name: Append a privilege
  oracle_grant:
    service_name: "xepdb1"
    username: "sys"
    password: "password"
    mode: "sysdba"
    grantee: "foo"
    privileges: "create table"
    state: "present"

- name: Remove a privilege
  oracle_grant:
    service_name: "xepdb1"
    username: "sys"
    password: "password"
    mode: "sysdba"
    grantee: "foo"
    privileges: "create table"
    state: "absent"
'''

RETURN = '''
ddls:
    description: Ordered list of DDL requests executed during module execution.
    returned: always
    type: list
    elements: str
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_db import OraDB

_PRIVILEGE_SEPARATOR = '::'


def get_existing_system_privileges(grantee):
    """Get the current system privileges of grantee."""
    rows = ora_db.execute_select('select privilege from dba_sys_privs where grantee = :grantee', {'grantee': grantee})
    return [item[0] for item in rows]


def get_existing_role_privileges(grantee):
    """Get the current role privileges of grantee."""
    rows = ora_db.execute_select('select granted_role from dba_role_privs where grantee = :grantee',
                                 {'grantee': grantee})
    return [item[0] for item in rows]


def get_existing_object_privileges(grantee):
    """Get the current object privileges of grantee."""
    rows = ora_db.execute_select("select p.owner || '.' || p.table_name || :sep || p.privilege"
                                 "  from dba_tab_privs p"
                                 " where p.grantee = :grantee", {'grantee': grantee, 'sep': _PRIVILEGE_SEPARATOR})
    return [item[0] for item in rows]


def is_directory(name):
    """Return True if name is a directory."""
    rows = ora_db.execute_select("select 1"
                                 "  from all_objects"
                                 " where owner = :owner and object_name = :name and object_type = 'DIRECTORY'",
                                 {'owner': name.split('.')[0], 'name': name.split('.')[1]})
    return len(rows) != 0


def execute_grant(grantee, privileges):
    if privileges:
        ora_db.execute_ddl('grant %s to %s' % (','.join(privileges), grantee))
        return True
    return False


def execute_object_grant(grantee, o_privileges):
    changed = False
    for (name, privileges) in _list_to_dict(o_privileges).items():
        ora_db.execute_ddl('grant %s on %s %s to %s' % (
            ','.join(privileges), 'directory' if is_directory(name) else '', name, grantee))
        changed = True
    return changed


def execute_revoke(grantee, privileges):
    if privileges:
        ora_db.execute_ddl('revoke %s from %s' % (','.join(privileges), grantee))
        return True
    return False


def execute_object_revoke(grantee, o_privileges):
    changed = False
    for (name, privileges) in _list_to_dict(o_privileges).items():
        ora_db.execute_ddl('revoke %s on %s %s from %s' % (
            ','.join(privileges), 'directory' if is_directory(name) else '', name, grantee))
        changed = True
    return changed


def _list_to_dict(o_p_list):
    """Transform a list of objects privileges to a dict of objects privileges."""
    object_privileges = {}
    for item in o_p_list:
        (name, privilege) = item.split(_PRIVILEGE_SEPARATOR)
        if name in object_privileges:
            object_privileges[name].append(privilege)
        else:
            object_privileges[name] = [privilege]
    return object_privileges


def ensure_privileges(grantee, privileges, o_privileges_list):
    """Set privileges to the grantee."""
    prev_privileges = get_existing_system_privileges(grantee) + get_existing_role_privileges(grantee)
    prev_privileges.sort()
    diff['before']['privileges'] = prev_privileges
    prev_object_privileges_list = get_existing_object_privileges(grantee)
    diff['before']['object_privileges'] = _list_to_dict(prev_object_privileges_list)

    # Get the difference between current grants and wanted grants
    privileges_to_add = set(privileges).difference(prev_privileges)
    privileges_to_remove = set(prev_privileges).difference(privileges)

    # Special case: if DBA is granted to a user, unlimited tablespace is also implicitly granted
    if 'DBA' in privileges and 'UNLIMITED TABLESPACE' not in privileges:
        privileges.append('UNLIMITED TABLESPACE')
    diff['after']['privileges'] = privileges

    # Get the difference between current objects privileges and target objects privileges
    o_privileges_to_add = set(o_privileges_list).difference(prev_object_privileges_list)
    o_privileges_to_remove = set(prev_object_privileges_list).difference(o_privileges_list)
    diff['after']['object_privileges'] = _list_to_dict(o_privileges_list)

    # Execute difference
    changed = execute_grant(grantee, privileges_to_add)
    changed = execute_revoke(grantee, privileges_to_remove) or changed
    changed = execute_object_grant(grantee, o_privileges_to_add) or changed
    changed = execute_object_revoke(grantee, o_privileges_to_remove) or changed

    if changed:
        module.exit_json(msg="Grants of grantee '%s' were changed." % grantee, diff=diff, ddls=ora_db.ddls,
                         changed=True)
    else:
        module.exit_json(msg="The grantee's privileges haven't changed.", diff=diff, ddls=ora_db.ddls, changed=False)


def append_privileges(grantee, privileges, o_privileges_list):
    """Append privileges to the grantee."""
    prev_privileges = get_existing_system_privileges(grantee) + get_existing_role_privileges(grantee)
    prev_privileges.sort()
    diff['before']['privileges'] = prev_privileges
    prev_object_privileges_list = get_existing_object_privileges(grantee)
    diff['before']['object_privileges'] = _list_to_dict(prev_object_privileges_list)

    # Keep only not existing privileges: the ones to add minus existing ones
    privileges = list(set(privileges) - set(prev_privileges))
    diff['after']['privileges'] = prev_privileges + privileges

    # Keep only not existing object privileges
    o_privileges_list = list(set(o_privileges_list) - set(prev_object_privileges_list))
    diff['after']['object_privileges'] = _list_to_dict(prev_object_privileges_list + o_privileges_list)

    # Execute difference
    changed = execute_grant(grantee, privileges)
    changed = execute_object_grant(grantee, o_privileges_list) or changed

    if changed:
        module.exit_json(msg="The grantee's privileges were changed.", diff=diff, ddls=ora_db.ddls, changed=True)
    else:
        module.exit_json(msg="The grantee's privileges haven't changed.", diff=diff, ddls=ora_db.ddls, changed=False)


def remove_privileges(grantee, privileges, o_privileges_list):
    """Remove privileges to the grantee."""
    prev_privileges = get_existing_system_privileges(grantee) + get_existing_role_privileges(grantee)
    prev_privileges.sort()
    diff['before']['privileges'] = prev_privileges
    prev_object_privileges_list = get_existing_object_privileges(grantee)
    diff['before']['object_privileges'] = _list_to_dict(prev_object_privileges_list)

    # Keep only existing privileges: intersection between the ones to remove and existing ones
    privileges = list(set(prev_privileges) & set(privileges))
    diff['after']['privileges'] = list(set(prev_privileges) - set(privileges))

    # Keep only existing object privileges
    o_privileges_list = list(set(prev_object_privileges_list) & set(o_privileges_list))
    diff['after']['object_privileges'] = _list_to_dict(list(set(prev_object_privileges_list) - set(o_privileges_list)))

    changed = execute_revoke(grantee, privileges)
    changed = execute_object_revoke(grantee, o_privileges_list) or changed

    if changed:
        module.exit_json(msg="The grantee's privileges were changed.", diff=diff, ddls=ora_db.ddls, changed=True)
    else:
        module.exit_json(msg="The grantee's privileges haven't changed.", diff=diff, ddls=ora_db.ddls, changed=False)


def main():
    global module
    global ora_db
    global diff

    module = AnsibleModule(
        argument_spec=dict(
            grantee=dict(type='str', required=True, aliases=['schema', 'role']),
            hostname=dict(type='str', default='localhost'),
            mode=dict(type='str', default='normal', choices=['normal', 'sysdba']),
            objects_privileges=dict(type='dict', default={}, aliases=['obj_privs']),
            oracle_home=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=True),
            port=dict(type='int', default=1521),
            privileges=dict(type='list', elements='str', default=[], aliases=['system_privileges', 'role_privileges']),
            service_name=dict(type='str', required=True),
            state=dict(type='str', default='identical', choices=['identical', 'present', 'absent']),
            username=dict(type='str', required=False),
        ),
        required_together=[['username', 'password']],
        supports_check_mode=True,
    )

    grantee = module.params['grantee']
    objects_privileges = module.params['objects_privileges']
    privileges = module.params['privileges']
    state = module.params['state']
    username = module.params['username']

    # Transforming parameters
    grantee = grantee.upper()
    privileges = [privilege.upper() for privilege in privileges]
    # Objects privileges are a dict: key is the name of the object and value is a list of privileges.
    o_privileges_list = []  # We're flattening the dict for comparison purpose.
    for o_name, o_privileges in (objects_privileges.items()):
        # If no owner is defined, the owner is the user connected with.
        if '.' not in o_name:
            o_name = username + '.' + o_name
        o_name = o_name.upper()
        for o_privilege in o_privileges:
            o_privileges_list.append(o_name + _PRIVILEGE_SEPARATOR + o_privilege.upper())

    ora_db = OraDB(module)
    diff = {'before': {'grantee': grantee}, 'after': {'grantee': grantee}}

    if state == 'identical':
        ensure_privileges(grantee, privileges, o_privileges_list)
    elif state == 'present':
        append_privileges(grantee, privileges, o_privileges_list)
    elif state == 'absent':
        remove_privileges(grantee, privileges, o_privileges_list)


if __name__ == '__main__':
    main()
