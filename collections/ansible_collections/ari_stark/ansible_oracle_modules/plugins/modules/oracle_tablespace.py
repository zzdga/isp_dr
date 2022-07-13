#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2014 Mikael Sandström <oravirt@gmail.com>
# Copyright: (c) 2020, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
module: oracle_tablespace
short_description: Manage Oracle tablespace objects
description:
    - This module manage Oracle tablespace objects.
    - It can create, alter or drop tablespaces and datafiles.
    - It supports permanent, undo and temporary tablespaces.
    - It supports online/offline state and read only/read write state.
    - It doesn't support defining default tablespace and other more specific actions.
version_added: "0.8.0"
author:
    - Mikael Sandström (@oravirt)
    - Ari Stark (@ari-stark)
options:
    autoextend:
        description:
            - This parameter indicates if the tablespace/datafile is autoextend.
            - When I(autoextend=false), I(nextsize) and I(maxsize) are ignored.
            - This parameter is ignored when I(state=absent).
        default: no
        type: bool
    bigfile:
        description:
            - This parameters indicates if the tablespace use one bigfile.
            - A tablespace can't be switch from smallfile to bigfile, and conversely.
            - This parameter is ignored when I(state=absent).
        default: no
        type: bool
    content:
        description:
            - The type of the tablespace to create/alter.
            - A tablespace's content can't be changed.
            - This parameter is ignored when I(state=absent).
        default: permanent
        choices: ['permanent', 'temp', 'undo']
        type: str
    datafiles:
        description:
            - List of the data files of the tablespace.
            - Element of the list can be a path (i.e '/u01/oradata/testdb/test01.dbf')
              or a ASM diskgroup (i.e '+DATA', not tested).
            - This parameter is mandatory when I(state!=absent).
        type: list
        elements: str
        aliases: ['datafile','df']
    default:
        description:
            - Define if this tablespace must be set as default database tablespace.
            - If I(default=True), the tablespace is set as the default tablespace.
            - If I(default=False), nothing is done, even if the tablespace is set as the default tablespace in database.
            - This option has no sense with an undo tablespace.
        default: false
        type: bool
    hostname:
        description:
            - Specify the host name or IP address of the database server computer.
        default: localhost
        type: str
    maxsize:
        description:
            - If I(autoextend=yes), the maximum size of the datafile (1M, 50M, 1G, etc.).
            - If not set, defaults to database limits.
            - This parameter is ignored when I(state=absent).
        type: str
        aliases: ['max']
    mode:
        description:
            - This option is the database administration privileges.
        default: normal
        type: str
        choices: ['normal', 'sysdba']
    nextsize:
        description:
            - If I(autoextend=yes), the size of the next extent allocated (1M, 50M, 1G, etc.).
            - If not set, defaults to database limits.
            - This parameter is ignored when I(state=absent).
        type: str
        aliases: ['next']
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
    read_only:
        description:
            - Specify the read status of the tablespace.
            - This parameter is ignored when I(state=absent).
        default: no
        type: bool
    service_name:
        description:
            - Specify the service name of the database you want to access.
        required: true
        type: str
    size:
        description:
            - Specify the size of the datafile (10M, 10G, 150G, etc.).
            - This parameter is ignored when I(state=absent).
            - This parameter is required when I(state!=absent).
        type: str
    state:
        description:
            - Specify the state of the tablespace/datafile.
            - I(state=present) and I(state=online) are synonymous.
            - If I(state=absent), the tablespace will be droped, including all datafiles.
        default: present
        type: str
        choices: ['present', 'online', 'offline', 'absent']
    tablespace:
        description:
            - The name of the tablespace to manage.
        type: str
        required: True
        aliases:
            - ts
            - name
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
    - A major change is to describe the tablespace (with its datafiles) for each execution.
      You have to describe instead of suggesting actions to do.
'''

EXAMPLES = '''
# Set a new normal tablespace
- oracle_tablespace:
    hostname: db-server-scan
    service_name: orcl
    username: system
    password: manager
    tablespace: test
    datafile: '+DATA'
    size: 100M
    state: present

# Create a new bigfile temporary tablespace with autoextend on and maxsize set
- oracle_tablespace:
    hostname: db-server
    service_name: orcl
    username: system
    password: manager
    tablespace: test
    datafile: '+DATA'
    content: temp
    size: 100M
    state: present
    bigfile: true
    autoextend: true
    next: 100M
    maxsize: 20G

# Drop a tablespace
- oracle_tablespace:
    hostname: localhost
    service_name: orcl
    username: system
    password: manager
    tablespace: test
    state: absent

# Make a tablespace read only
- oracle_tablespace:
    hostname: localhost
    service_name: orcl
    username: system
    password: manager
    tablespace: test
    datafile: '+DATA'
    size: 100M
    read_only: yes

# Make a tablespace offline
- oracle_tablespace:
    hostname: localhost
    service_name: orcl
    username: system
    password: manager
    tablespace: test
    datafile: '+DATA'
    size: 100M
    state: offline
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
from ansible_collections.ari_stark.ansible_oracle_modules.plugins.module_utils.ora_object import (ContentType, Datafile,
                                                                                                  FileType)


def get_existing_tablespace(tablespace):
    """Search for an existing tablespace in database"""
    sql = "select distinct coalesce(df.online_status, ts.status), ts.status, ts.bigfile, ts.contents" \
          "  from dba_tablespaces ts, dba_data_files df, dba_temp_files tf" \
          " where ts.tablespace_name = :tn" \
          "   and ts.tablespace_name = df.tablespace_name(+)" \
          "   and ts.tablespace_name = tf.tablespace_name(+)"

    sql_is_default = "select 1" \
                     "  from database_properties dp" \
                     " where property_name in ('DEFAULT_PERMANENT_TABLESPACE', 'DEFAULT_TEMP_TABLESPACE')" \
                     "   and property_value = :tn"

    params = {'tn': tablespace}

    # One tablespace max can exist with a specific name and every data file should have the same online_status.
    row = ora_db.execute_select(sql, params, fetchone=True)

    if row:
        # Convert data
        state = 'online' if row[0] == 'ONLINE' else 'offline'
        read_only = (row[1] == 'READ ONLY')
        file_type = FileType(row[2] == 'YES')
        content_type = ContentType({'PERMANENT': 'permanent', 'UNDO': 'undo', 'TEMPORARY': 'temp'}[row[3]])

        diff['before']['state'] = state
        diff['before']['read_only'] = read_only
        diff['before']['bigfile'] = file_type.is_bigfile()
        diff['before']['content'] = content_type.content

        is_default = bool(ora_db.execute_select(sql_is_default, params, fetchone=True))
        diff['before']['default'] = is_default

        # Get previous datafiles
        datafiles = get_existing_datafiles(tablespace)

        return {'state': state, 'read_only': read_only, 'file_type': file_type, 'content_type': content_type,
                'datafiles': datafiles, 'default': is_default}
    else:
        diff['before']['state'] = 'absent'
        return None


def get_existing_datafiles(tablespace):
    """Search for all existing datafiles for a specific tablespace"""
    sql = "select df.file_name, df.bytes, df.autoextensible, df.increment_by * ts.block_size, df.maxbytes," \
          "       ts.bigfile, ts.block_size" \
          "  from dba_tablespaces ts, dba_data_files df" \
          " where ts.tablespace_name = :tn" \
          "   and ts.tablespace_name = df.tablespace_name" \
          " union all " \
          "select df.file_name, df.bytes, df.autoextensible, df.increment_by * ts.block_size, df.maxbytes," \
          "       ts.bigfile, ts.block_size" \
          "  from dba_tablespaces ts, dba_temp_files df" \
          " where ts.tablespace_name = :tn" \
          "   and ts.tablespace_name = df.tablespace_name"
    params = {'tn': tablespace}

    rows = ora_db.execute_select(sql, params)
    datafiles = []

    for row in rows:
        datafiles.append(
            Datafile(path=row[0], size=row[1], autoextend=row[2] == 'YES', nextsize=row[3], maxsize=row[4],
                     bigfile=row[5] == 'YES', block_size=row[6]))
    diff['before']['datafiles'] = [datafile.asdict() for datafile in datafiles]
    return datafiles


def ensure_datafile_state(prev_tablespace, tablespace, datafiles, content_type):
    """Ensure the data files are in the correct state (size, autoextend) and exists or not"""
    changed = False
    prev_datafile_paths = [datafile.path for datafile in prev_tablespace['datafiles']]

    # For each wanted data files
    for datafile in datafiles:
        # If it exists, check if we have to change it
        if datafile.path in prev_datafile_paths:
            prev_datafile = [d for d in prev_tablespace['datafiles'] if d.path == datafile.path][0]
            # What can change if not autoextend : size
            if datafile.needs_resize(prev_datafile):
                ora_db.execute_ddl("alter database datafile '%s' resize %s" % (datafile.path, datafile.size))
                changed = True

            # What can change if autoextend : next_size and max_size
            if datafile.needs_change_autoextend(prev_datafile):
                ora_db.execute_ddl("alter database %s '%s' %s" % (
                    content_type.datafile_clause(), datafile.path, datafile.autoextend_clause()))
                changed = True
        else:  # or create it
            ora_db.execute_ddl(
                'alter tablespace %s add %s %s' % (
                    tablespace, content_type.datafile_clause(), datafile.data_file_clause()))
            changed = True

    wanted_datafile_paths = [datafile.path for datafile in datafiles]

    # For each existing data files
    for datafile in prev_tablespace['datafiles']:
        # If it isn't wanted, drop it
        if datafile.path not in wanted_datafile_paths:
            ora_db.execute_ddl(
                "alter tablespace %s drop %s '%s'" % (tablespace, content_type.datafile_clause(), datafile.path))
            changed = True

    return changed


def ensure_present(tablespace, state, read_only, datafiles, file_type, content_type, default):
    """Create the tablespace if it doesn't exist, or alter it if it is different"""
    prev_tablespace = get_existing_tablespace(tablespace)
    diff['after']['datafiles'] = [datafile.asdict() for datafile in datafiles]

    # Tablespace exists
    if prev_tablespace:
        changed = False

        # Check file type, because we can't switch from one to another.
        if not prev_tablespace['file_type'].__eq__(file_type):
            module.fail_json(msg='Cannot convert tablespace %s from %s to %s !' %
                                 (tablespace, prev_tablespace['file_type'], file_type),
                             diff=diff, ddls=ora_db.ddls)

        # Check content type, because we can't switch from one to another.
        if not prev_tablespace['content_type'].__eq__(content_type):
            module.fail_json(msg='Cannot convert tablespace %s from %s to %s !' %
                                 (tablespace, prev_tablespace['content_type'], content_type),
                             diff=diff, ddls=ora_db.ddls)

        if ensure_datafile_state(prev_tablespace, tablespace, datafiles, content_type):
            changed = True

        # Managing online/offline state
        if prev_tablespace['state'] != state:
            ddl = 'alter tablespace %s %s' % (tablespace, state)
            ora_db.execute_ddl(ddl)
            changed = True

        # Managing read write/read only state
        if prev_tablespace['read_only'] != read_only:
            ddl = 'alter tablespace %s %s' % (tablespace, 'read only' if read_only else 'read write')
            ora_db.execute_ddl(ddl)
            changed = True

        # Managing default tablespace
        if default and not prev_tablespace['default']:
            ddl = 'alter database default %s tablespace %s' % (content_type.create_clause(), tablespace)
            ora_db.execute_ddl(ddl)
            changed = True

        # Nothing more to do.
        if changed:
            module.exit_json(changed=True, msg="Tablespace %s changed." % tablespace, diff=diff, ddls=ora_db.ddls)
        else:
            module.exit_json(changed=False, msg="Tablespace %s already exists." % tablespace, diff=diff,
                             ddls=ora_db.ddls)
    else:  # Tablespace needs to be created
        files_specifications = ', '.join(datafile.data_file_clause() for datafile in datafiles)
        ddl = 'create %s %s tablespace %s %s %s' % (
            file_type, content_type.create_clause(), tablespace, content_type.datafile_clause(), files_specifications)
        ora_db.execute_ddl(ddl)

        # Managing default tablespace
        if default:
            ddl = 'alter database default %s tablespace %s' % (content_type.create_clause(), tablespace)
            ora_db.execute_ddl(ddl)

        if read_only:
            ddl = 'alter tablespace %s read only' % tablespace
            ora_db.execute_ddl(ddl)

        module.exit_json(changed=True, msg='Tablespace %s created.' % tablespace, diff=diff, ddls=ora_db.ddls)


def ensure_absent(tablespace):
    """Drop the tablespace if it exists"""
    prev_tablespace = get_existing_tablespace(tablespace)

    if prev_tablespace:
        ora_db.execute_ddl('drop tablespace %s including contents and datafiles' % tablespace)
        module.exit_json(changed=True, msg='Tablespace %s dropped.' % tablespace, diff=diff, ddls=ora_db.ddls)
    else:
        module.exit_json(changed=False, msg="Tablespace %s doesn't exist." % tablespace, diff=diff, ddls=ora_db.ddls)


def main():
    global module
    global ora_db
    global diff

    module = AnsibleModule(
        argument_spec=dict(
            autoextend=dict(type='bool', default=False),
            bigfile=dict(type='bool', default=False),
            content=dict(type='str', default='permanent', choices=['permanent', 'temp', 'undo']),
            datafiles=dict(type='list', elements='str', default=[], aliases=['datafile', 'df']),
            default=dict(type='bool', default=False),
            hostname=dict(type='str', default='localhost'),
            maxsize=dict(type='str', required=False, aliases=['max']),
            mode=dict(type='str', default='normal', choices=['normal', 'sysdba']),
            oracle_home=dict(type='str', required=False),
            nextsize=dict(type='str', required=False, aliases=['next']),
            password=dict(type='str', required=False, no_log=True),
            port=dict(type='int', default=1521),
            read_only=dict(type='bool', default=False),
            service_name=dict(type='str', required=True),
            size=dict(type='str', required=False),
            state=dict(type='str', default='present',
                       choices=['present', 'online', 'offline', 'absent']),
            tablespace=dict(type='str', required=True, aliases=['name', 'ts']),
            username=dict(type='str', required=False, aliases=['user']),
        ),
        required_together=[['username', 'password']],
        required_if=[['state', 'present', ['size']],
                     ['state', 'online', ['size']],
                     ['state', 'offline', ['size']]],
        supports_check_mode=True,
    )

    autoextend = module.params['autoextend']
    bigfile = module.params['bigfile']
    content = module.params['content']
    datafile_names = module.params['datafiles']
    default = module.params['default']
    maxsize = module.params['maxsize']
    nextsize = module.params['nextsize']
    read_only = module.params['read_only']
    size = module.params['size']
    state = module.params['state']
    tablespace = module.params['tablespace']

    # Transforming parameters
    tablespace = tablespace.upper()
    if state == 'present':  # Present is synonymous for online.
        state = 'online'
    datafiles = []
    for datafile_name in datafile_names:
        datafile = Datafile(datafile_name, size, autoextend, nextsize, maxsize, bigfile)
        datafiles.append(datafile)
    file_type = FileType(bigfile)
    content_type = ContentType(content)

    ora_db = OraDB(module)

    # Initializing diff
    diff = {'before': {'tablespace': tablespace},
            'after': {'tablespace': tablespace,
                      'state': state,
                      'read_only': read_only,
                      'bigfile': file_type.is_bigfile(),
                      'content': content_type.content,
                      'default': default, }}

    # Doing actions
    if state in ('online', 'offline'):
        ensure_present(tablespace, state, read_only, datafiles, file_type, content_type, default)
    elif state == 'absent':
        ensure_absent(tablespace)


if __name__ == '__main__':
    main()
