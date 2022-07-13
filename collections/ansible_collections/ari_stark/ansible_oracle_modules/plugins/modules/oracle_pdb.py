#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2014 Mikael Sandström <oravirt@gmail.com>
# Copyright: (c) 2020, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: oracle_pdb
short_description: Manage Oracle pluggable databases
description:
    - This module manages Oracle pluggable databases.
    - It can create PDB from seed, clone PDB or plug PDB from XML ;
      drop or unplug a PDB ; open or close a PDB.
    - Only a few options are available to create, drop or alter a pluggable database.
    - "To create of a PDB, you have to use one of these three options : I(clone_from),
      I(pdb_admin_username) or I(plug_file)."
    - The check of the parameters are minimal,
      full responsability is delegated to Oracle to check if parameters are corrects.
version_added: "0.8.0"
author:
    - Mikael Sandström (@oravirt)
    - Ari Stark (@ari-stark)
options:
    clone_from:
        description:
            - This option is the name of the PDB to clone.
            - It will trigger the creation of the PDB as a clone.
            - It can be used in conjunction with the option I(snapshot_copy).
            - It is mutually exclusive with I(pdb_admin_username) and I(plug_file).
        required: False
        type: str
    file_dest:
        description:
            - Specify the file_dest clause.
        required: False
        type: str
    file_name_convert:
        description:
            - Specify the file_name_convert clause.
        default: {}
        type: dict
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
    pdb_admin_password:
        description:
            - Set the password for the PDB admin.
            - This option must be used with I(pdb_admin_username).
        required: False
        type: str
        aliases: ['admin_pass']
    pdb_admin_username:
        description:
            - Set the username of the PDB admin.
            - This option must be used with I(pdb_admin_password).
            - It will trigger the creation of the PDB from a seed.
            - It is mutually exclusive with I(clone_from) and I(plug_file).
        required: False
        type: str
        aliases: ['admin_user']
    pdb_name:
        description:
            - The name of the PDB to manage.
        required: True
        type: str
    plug_file:
        description:
            - Set the XML file to use to plug a disconnected PDB.
            - It will trigger the creation of the PDB from a XML.
            - If I(file_name_convert) is defined, the tablespace files are copied to the new location.
            - If I(file_name_convert) is not defined, the clause NOCOPY is used.
            - It is mutually exclusive with I(clone_from) and I(pdb_admin_username).
        required: False
        type: str
    port:
        description:
            - Specify the listening port on the database server.
        default: 1521
        type: int
    read_only:
        description:
            - Defines if the PDB is to be opened in read only.
            - This option has meaning only with I(state=opened)
        default: False
        type: bool
    roles:
        description:
            - This option is to define roles for the PDB admin.
            - This option has meaning only with I(pdb_admin_username).
        default: []
        type: list
        elements: str
    service_name:
        description:
            - Specify the service name of the database you want to access.
            - The service name is the service to access the CDB.
        required: true
        type: str
        aliases: ['cdb_name']
    snapshot_copy:
        description:
            - This option is to define if the clone to create will be a snapshot copy.
            - This option has meaning only with I(clone_from).
        default: False
        type: bool
    state:
        description:
            - Change the state of a PDB.
            - Unless one of I(clone_from), I(pdb_admin_username) or I(plug_file) is defined, the PDB won't be created.
            - If the PDB already exists, the options used for creation will be ignored.
            - If I(absent), PDB will be dropped with existing files or unplugged.
            - If I(closed), PDB will be closed if it exists.
            - If I(opened), PDB will be opened if it exists.
            - If I(present), the state of the PDB will be returned if it exists. It's a simple check of PDB existence.
            - If the PDB doesn't exist, is not created and the state I(closed), I(opened) and I(present)
               are used, the task will fail.
        default: opened
        choices: ['absent', 'closed', 'opened', 'present']
        type: str
    unplug_file:
        description:
            - Set the XML file to use to unplug an existing PDB.
            - This option has meaning only when used with I(state=absent).
            - If the PDB doesn't exists, this option won't do anything.
        required: False
        type: str
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
    - Changes made by @ari-stark broke previous module interface.
'''

EXAMPLES = '''
- name: Open a PDB in read write
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "opened"

- name: Open a PDB in read only
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "opened"
    read_only: yes

- name: Remove a PDB
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "absent"

- name: Creates a PDB
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "opened"
    pdb_admin_username: "foo"
    pdb_admin_password: "bar"
    file_name_convert:
        "/opt/oracle/oradata/XE/pdbseed": "/tmp/xepdb2/dbf01"

- name: Check the PDB exists. Do nothing but return the state of the PDB.
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "present"

- name: Unplug a PDB
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB2"
    state: "absent"
    unplug_file: "/tmp/xepdb2.xml"

- name: Plug in a PDB to a new location
  oracle_pdb:
    hostname: "localhost"
    service_name: "XE"
    username: "sys"
    password: "password"
    mode: "sysdba"
    pdb_name: "XEPDB3"
    state: "opened"
    plug_file: "/tmp/xepdb2.xml"
    file_name_convert:
        "/tmp/xepdb2/dbf01": "/tmp/xepdb3/dbf01"
'''

RETURN = '''
ddls:
    description: Ordered list of DDL requests executed during module execution.
    returned: always
    type: list
    elements: str
pdb_name:
    description: The name of the PDB.
    returned: when I(state=present)
    type: str
state:
    description: The state of the PDB.
    returned: when I(state=present)
    type: str
read_only:
    description: If the PDB is opened in read only.
    returned: when I(state=present)
    type: bool
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_db import OraDB


def get_existing_pdb(pdb_name):
    """Get the data of the existing PDB."""
    result = ora_db.execute_select('select name, open_mode from v$pdbs where name = :name', {'name': pdb_name})

    if result:
        pdb_name = result[0][0]
        open_mode = result[0][1]
        map_open_mode = {'MOUNTED': 'closed', 'READ ONLY': 'opened', 'READ WRITE': 'opened'}
        diff['before']['state'] = map_open_mode[open_mode]
        diff['before']['read_only'] = open_mode == 'READ ONLY'
        return {'pdb_name': pdb_name, 'state': map_open_mode[open_mode], 'read_only': open_mode == 'READ ONLY'}
    else:
        diff['before']['state'] = 'absent'
        return None


def create_pdb(pdb_name, pdb_admin_username, pdb_admin_password, clone_from, snapshot_copy, plug_file, file_dest,
               file_name_convert, roles):
    """Create a PDB."""
    create_ddl = 'create pluggable database %s' % pdb_name
    if pdb_admin_username:  # Create from seed
        create_ddl += ' admin user %s identified by "%s"' % (pdb_admin_username, pdb_admin_password)
    elif clone_from:  # Clone an existing PDB
        create_ddl += ' from %s %s' % (clone_from, 'snapshot copy' if snapshot_copy else '')
    elif plug_file:  # Plug a PDB / create from XML
        create_ddl += " using '%s' %s" % (plug_file, 'copy' if file_name_convert else 'nocopy')

    if roles:
        create_ddl += ' roles = (%s)' % ','.join(roles)

    if file_name_convert:
        elements = ','.join("'%s', '%s'" % (key, value) for (key, value) in file_name_convert.items())
        create_ddl += ' file_name_convert = (%s)' % elements

    if file_dest:
        create_ddl += " create_file_dest = '%s'" % file_dest

    ora_db.execute_ddl(create_ddl)


def ensure_present(pdb_name):
    """Ensure a PDB is present."""
    if existing_pdb:
        module.exit_json(msg='PDB %s exists.' % pdb_name, changed=changed(), diff=diff, ddls=ora_db.ddls,
                         **existing_pdb)
    else:
        module.fail_json(msg="PDB %s doesn't exist." % pdb_name, changed=changed(), ddls=ora_db.ddls)


def ensure_opened(pdb_name, read_only):
    """Ensure a PDB is opened."""
    if not existing_pdb:
        module.fail_json(msg="PDB %s doesn't exist." % pdb_name, changed=changed(), ddls=ora_db.ddls)

    if existing_pdb['state'] != 'opened' or existing_pdb['read_only'] != read_only:
        ora_db.execute_ddl(
            'alter pluggable database %s open %s force' % (pdb_name, 'read only' if read_only else 'read write'))
    module.exit_json(msg='PDB %s is opened.' % pdb_name, changed=changed(), diff=diff, ddls=ora_db.ddls)


def ensure_closed(pdb_name):
    """Ensure a PDB is closed."""
    if not existing_pdb:
        module.fail_json(msg="PDB %s doesn't exist." % pdb_name, changed=changed(), ddls=ora_db.ddls)

    if existing_pdb['state'] != 'closed':
        ora_db.execute_ddl('alter pluggable database %s close immediate instances = all' % pdb_name)
    module.exit_json(msg='PDB %s is closed.' % pdb_name, changed=changed(), diff=diff, ddls=ora_db.ddls)


def ensure_absent(pdb_name, unplug_file):
    """Ensure a PDB is absent."""
    if not existing_pdb:
        module.exit_json(msg="PDB %s doesn't exist." % pdb_name, changed=changed(), diff=diff, ddls=ora_db.ddls)

    if existing_pdb['state'] == 'opened':
        ora_db.execute_ddl('alter pluggable database %s close immediate instances = all' % pdb_name)

    if unplug_file:
        ora_db.execute_ddl("alter pluggable database %s unplug into '%s'" % (pdb_name, unplug_file))
        ora_db.execute_ddl('drop pluggable database %s keep datafiles' % pdb_name)
    else:
        ora_db.execute_ddl('drop pluggable database %s including datafiles' % pdb_name)
    module.exit_json(msg='PDB %s dropped.' % pdb_name, changed=changed(), diff=diff, ddls=ora_db.ddls)


def changed():
    return len(ora_db.ddls) != 0


def main():
    global module
    global ora_db
    global diff
    global existing_pdb

    module = AnsibleModule(
        argument_spec=dict(
            clone_from=dict(type='str', required=False),
            file_dest=dict(type='str', required=False),
            file_name_convert=dict(type='dict', default={}),
            hostname=dict(type='str', default='localhost'),
            mode=dict(type='str', default='normal', choices=['sysdba', 'normal']),
            oracle_home=dict(type='str', required=False),
            password=dict(type='str', no_log=True),
            pdb_admin_password=dict(type='str', required=False, no_log=True, aliases=['admin_pass']),
            pdb_admin_username=dict(type='str', required=False, aliases=['admin_user']),
            pdb_name=dict(type='str', required=True),
            plug_file=dict(type='str', required=False),
            port=dict(type='int', default=1521),
            read_only=dict(type='bool', default=False),
            roles=dict(type='list', elements='str', default=[]),
            service_name=dict(type='str', required=True, aliases=['cdb_name']),
            snapshot_copy=dict(type='bool', default=False),
            state=dict(type='str', default='opened', choices=['absent', 'closed', 'opened', 'present']),
            unplug_file=dict(type='str', required=False),
            username=dict(type='str', aliases=['user']),

        ),
        required_together=[['username', 'password'],
                           ['pdb_admin_username', 'pdb_admin_password'],
                           ],
        mutually_exclusive=[['pdb_admin_username', 'clone_from', 'plug_file']],
        supports_check_mode=True,
    )

    clone_from = module.params['clone_from']
    file_dest = module.params['file_dest']
    file_name_convert = module.params['file_name_convert']
    pdb_admin_password = module.params['pdb_admin_password']
    pdb_admin_username = module.params['pdb_admin_username']
    pdb_name = module.params['pdb_name']
    plug_file = module.params['plug_file']
    read_only = module.params['read_only']
    roles = module.params['roles']
    snapshot_copy = module.params['snapshot_copy']
    state = module.params['state']
    unplug_file = module.params['unplug_file']

    ora_db = OraDB(module)
    diff = {'before': {'pdb_name': pdb_name},
            'after': {'pdb_name': pdb_name, 'state': state, 'read_only': read_only}}
    existing_pdb = get_existing_pdb(pdb_name)  # Get existing PDB

    if not existing_pdb and (clone_from or pdb_admin_username or plug_file) \
            and state in ['closed', 'opened', 'present']:
        create_pdb(pdb_name, pdb_admin_username, pdb_admin_password, clone_from, snapshot_copy, plug_file, file_dest,
                   file_name_convert, roles)
        existing_pdb = {'name': pdb_name, 'state': 'closed', 'read_only': False}  # Fake PDB state after creation

    if state == 'absent':
        ensure_absent(pdb_name, unplug_file)
    elif state == 'closed':
        ensure_closed(pdb_name)
    elif state == 'opened':
        ensure_opened(pdb_name, read_only)
    elif state == 'present':
        ensure_present(pdb_name)


if __name__ == '__main__':
    main()
