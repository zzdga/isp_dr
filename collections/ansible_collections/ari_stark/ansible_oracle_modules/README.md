# ansible-oracle-modules #

## Fork from oravirt/ansible-oracle-modules

This project is a fork from https://github.com/oravirt/ansible-oracle-modules made by @oravirt.

### Difference from @oravirt project ###

The purpose of the fork is to :
1. use Ansible standards (check mode, diff mode, ansible-doc, ansible-test, ...),
1. clean code,
1. reuse code with _module_utils_,
1. change the gathering of modules into a [collection](https://galaxy.ansible.com/ari_stark/ansible_oracle_modules) to ease its use and versioning,
1. fix bugs, add features, add tests.

## Usage ##

Theses modules are a collection on Ansible Galaxy.
The collection page is here : https://galaxy.ansible.com/ari_stark/ansible_oracle_modules.

## Oracle modules for Ansible ##

### Pre-requisite ###

The Python module `cx_Oracle` needs to be installed on the Ansible host. (`pip install cx_Oracle`)

### Modules forked from @oravirt's ###

#### oracle_directory ####

- This module manages Oracle directory objects.
- It can create, replace or drop directories.

#### oracle_facts ####

- This module return some facts about Oracle database.
- It requires privileges to access v$database.
- The option `gather_subset` can filter facts to gather and return.

#### oracle_grant ####

- This module manages Oracle privileges.
- It can deal with system privileges, role privileges and object privileges (procedure, function, package, package body and directory).
- It has 3 possible states: `present`, `absent` and `identical`.
  States `present` and `absent` ensure privileges are present or absent.
  State `identical` replace privileges with the ones in parameter.

#### oracle_parameter ####

- This module manages parameters in an Oracle database (i.e _alter system set param=value_).
- Parameters value comparison is case sensitive, module wise. To avoid Ansible *changed* state, check the case of the value.
- Hidden parameters can be changed using sysdba privileges.

**Note:**
When specifying sga-parameters the database requests memory based on granules which are variable in size depending on the size requested,
and that means the database may round the requested value to the nearest multiple of a granule.
e.g sga_max_size=1500M will be rounded up to 1504 (which is 94 granules of 16MB). That will cause the displayed value to be 1504M, which has
the effect that the next time the module is is run with a desired value of 1500M it will be changed again.
So that is something to consider when setting parameters that affects the SGA.

#### oracle_pdb ####

- This module manages pluggable databases (PDB) in an Oracle container database (CDB).
- It can :
  * create a PDB from seed, clone a PDB or plug a PDB from XML ;
  * drop or unplug a PDB ;
  * open or close a PDB.
- Only a few Oracle options are available to create, drop or alter a pluggable database.

#### oracle_quota ####

- This module manages Oracle quota for users.
- It can ensure a single quota is present/absent.
- It can ensure a list of quotas matches the quotas in database.
- It can ensure a user has no quota.
- Username and tablespace name are case insensitive.

#### oracle_role ####

- This module manages Oracle role objects.
- It handles creation and deletion of roles.
- It doesn't support changing password. There's no hint to know a password was changed, so no change is made.

#### oracle_sql ####

- This module executes SQL queries or PL/SQL blocks.
- It can be used to execute select statements to fetch data from database.
- It can be used to execute arbitrary SQL statement. Connection is set to autocommit, so there's no transaction management.
- It can be used to execute PL/SQL blocks.
- It cannot execute SQL statements and PL/SQL blocks in one call.
- Its inputs are direct SQL or a file containing SQL.

#### oracle_tablespace ####

- This module manages Oracle tablespace objects.
- It can create, alter or drop tablespaces and datafiles.
- It supports permanent, undo and temporary tablespaces.
- It supports online/offline state and read only/read write state.
- It doesn't support defining default tablespace and other more specific actions.
- It supports check mode, diff mode and it returns DDL requests executed by the module.

#### oracle_user ####

- This module manages Oracle user/schema.
- It can create, alter or drop users.
- It can empty schemas (droping all its content).
- It can change password of users ; lock/unlock and expire/unexpire accounts.
- It can't be used to give privileges (refer to oracle_grant).

### Modules identical to @oravirt's (sort of) ###

#### oracle_asmdg ####

pre-req: cx_Oracle

- Manages ASM diskgroup state. (absent/present)
- Takes a list of disks and makes sure those disks are part of the DG.
If the disk is removed from the disk it will be removed from the DG.
- Also manages attributes

**Note:**
- Supports redundancy levels, but does not yet handle specifying failuregroups

#### oracle_asmvol ####

- Manages ASM volumes. (absent/present)

#### oracle_awr ####

pre-req: cx_Oracle, datetime

- Manages AWR snapshot settings

#### oracle_datapatch ####

#### oracle_db ####

pre-rec: cx_Oracle

- Create/remove databases (cdb/non-cdb)
- Can be created by passing in a responsefile or just by using parameters

#### oracle_gi_facts ####

- Gathers facts about Grid Infrastructure cluster configuration

#### oracle_job ####

pre-req: cx_Oracle, re

- Manages DBMS_SCHEDULER jobs

#### oracle_jobclass ####

pre-req: cx_Oracle

- Manages DBMS_SCHEDULER job classes

#### oracle_jobschedule ####

pre-req: cx_Oracle, re

- Manages DBMS_SCHEDULER job schedules

#### oracle_jobwindow ####

pre-req: cx_Oracle, datetime

- Manages DBMS_SCHEDULER windows

#### oracle_ldapuser ####

pre-req: cx_Oracle, ldap, re

- Syncronises users/role grants from LDAP/Active Directory to the database

#### oracle_opatch ####

#### oracle_profile ####

#### oracle_redo ####

pre-rec: cx_Oracle

- Manage redo-groups and their size in RAC or single instance environments
- NOTE: For RAC environments, the database needs to be in ARCHIVELOG mode. This is not required for SI environments.

#### oracle_rsrc_consgroup ####

pre-req: cx_Oracle, re

- Manages resource manager consumer groups including its mappings and grants

#### oracle_services ####

pre-req: cx_Oracle (if GI is not running)

- Manages services in an Oracle database (RAC/Single instance)

**Note:**
At the moment, Idempotence only applies to the state (present,absent,started, stopped). No other options are considered.

#### oracle_stats_prefs ####

pre-req: cx_Oracle

- Managing DBMS_STATS global preferences

## Tests ##

Tests are made against an Oracle XE 18.4 database. Tests are now started with ansible-test.

* Compile and sanity tests were run against Python 2.7 and 3.5 to 3.9. There's still a lot of change to make to comply to sanity tests, but compile error should all be fixed.
* Integration tests for refactored modules are available in `tests/integration`.
* Unit tests are available in `tests/unit`.
* Lots of tests are still missing, specificaly for non refactored modules.

To run tests:
* `ansible-test sanity --docker default`
* `ansible-test units --docker default --python [2.7|3.6|...]`
* `ansible-test integration` (requires a local database, and only run with Ansible version >=2.10 due to the use or community.general.json_query filter)

To run code coverage:
* `ansible-test coverage erase`
* `ansible-test integration --coverage`
* `ansible-test coverage report` or `ansible-test coverage html` for more details.
