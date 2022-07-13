#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: oracle_directory
short_description: Manage Oracle directory objects
description:
    - This module manage Oracle directory objects.
    - It can create, replace or drop directories.
version_added: "0.9.0"
author: Ari Stark (@ari-stark)
options:
    directory_name:
        description:
            - The name of the directory being managed.
        required: true
        type: 'str'
        aliases:
            - 'name'
            - 'directory'
    directory_path:
        description:
            - The path to the directory being managed.
            - Not required when I(state=absent).
        required: false
        type: 'str'
        aliases:
            - 'path'
    hostname:
        description:
            - Specify the host name or IP address of the database server computer.
        default: 'localhost'
        type: 'str'
    mode:
        description:
            - This option is the database administration privileges.
        default: 'normal'
        choices:
            - 'normal'
            - 'sysdba'
        type: 'str'
    oracle_home:
        description:
            - Define the directory into which all Oracle software is installed.
            - Define ORACLE_HOME environment variable if set.
        required: false
        type: 'str'
    password:
        description:
            - Set the password to use to connect the database server.
            - Must not be set if using Oracle wallet.
        required: false
        type: 'str'
    port:
        description:
            - Specify the listening port on the database server.
        default: 1521
        type: 'int'
    service_name:
        description:
            - Specify the service name of the database you want to access.
        required: true
        type: 'str'
        aliases:
            - 'tns'
    state:
        description:
            - Define the state of the directory being managed.
            - If I(present), directory will be created if it does not exist or modified if the path is different.
            - If I(absent), directory will be dropped if it exists.
        default: 'present'
        choices:
            - 'present'
            - 'absent'
        type: 'str'
    username:
        description:
            - Set the login to use to connect the database server.
            - Must not be set if using Oracle wallet.
        required: false
        type: 'str'
requirements:
    - Python module cx_Oracle
    - Oracle basic tools.
notes:
    - Check mode and diff mode are supported.
'''

EXAMPLES = '''
- name: create a directory
  oracle_directory:
    hostname: 127.0.0.1
    port: 1521
    service_name: pdbtest
    username: sys
    password: password
    mode: sysdba
    directory_name: dir
    directory_path: /data/imp
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


def get_existing_directory(directory_name):
    """Search for an existing directory in database."""
    row = ora_db.execute_select('select directory_name, directory_path from all_directories where directory_name = :dn',
                                {'dn': directory_name}, fetchone=True)

    if row:
        diff['before']['state'] = 'present'
        diff['before']['path'] = row[1]
        return {'directory_name': row[0], 'directory_path': row[1]}
    else:
        diff['before']['state'] = 'absent'
        return None


def ensure_present(directory_name, directory_path):
    """Create or replace directory if needed."""
    prev_directory = get_existing_directory(directory_name)
    diff['after']['path'] = directory_path

    if prev_directory is None:
        ora_db.execute_ddl("create directory %s as '%s'" % (directory_name, directory_path))
        module.exit_json(changed=True, message='Directory %s created' % directory_name, diff=diff, ddls=ora_db.ddls)
    elif prev_directory['directory_path'] != directory_path:
        ora_db.execute_ddl("create or replace directory %s as '%s'" % (directory_name, directory_path))
        module.exit_json(changed=True, message='Directory %s replaced' % directory_name, diff=diff, ddls=ora_db.ddls)
    else:
        module.exit_json(changed=False, message='Directory %s already exists' % directory_name, diff=diff,
                         ddls=ora_db.ddls)


def ensure_absent(directory_name):
    """Drop directory if needed."""
    prev_directory = get_existing_directory(directory_name)

    if prev_directory is None:
        module.exit_json(changed=False, message="Directory %s doesn't exist" % directory_name, diff=diff,
                         ddls=ora_db.ddls)
    else:
        ora_db.execute_ddl("drop directory %s" % directory_name)
        module.exit_json(changed=True, message='Directory %s dropped.' % directory_name, diff=diff, ddls=ora_db.ddls)


def main():
    global module
    global ora_db
    global diff

    module = AnsibleModule(
        argument_spec=dict(
            directory_name=dict(type='str', required=True, aliases=['name', 'directory']),
            directory_path=dict(type='str', required=False, aliases=['path']),
            hostname=dict(type='str', default='localhost'),
            mode=dict(type='str', default='normal', choices=['normal', 'sysdba']),
            oracle_home=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=True),
            port=dict(type='int', default=1521),
            service_name=dict(type='str', required=True, aliases=['tns']),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            username=dict(type='str', required=False),
        ),
        required_together=[['username', 'password']],
        required_if=[['state', 'present', ['directory_path']]],
        supports_check_mode=True,
    )

    directory_name = module.params['directory_name']
    directory_path = module.params['directory_path']
    state = module.params['state']

    ora_db = OraDB(module)
    # Initialize diff
    diff = {'before': {'name': directory_name},
            'after': {'name': directory_name, 'state': state}}

    # Doing action
    if state == 'present':
        ensure_present(directory_name, directory_path)
    else:
        ensure_absent(directory_name)


if __name__ == '__main__':
    main()
