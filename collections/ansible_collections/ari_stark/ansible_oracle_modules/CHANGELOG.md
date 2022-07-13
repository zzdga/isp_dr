# Changelog #

## 1.2.1 ##

* Add drop of materialized view and trigger on emptying schema.

## 1.2.0 ##

* Add module oracle_quota
* Create a module utils ora_object which can contain classes to manage Oracle objects (ie. size clause).
* Move inner classes from oracle_tablespace to ora_object.
* Fix sanity tests on module oracle_services.

## 1.1.2 ##

* Adapt unit tests to ansible-test usage

## 1.1.1 ##

* Adapt integration tests to ansible-test usage

## 1.1.0 ##

* Refactor oracle_parameter module
* Fix ora_db to display ddls on error
* Fix oracle_user to better check parameters

## 1.0.2 ##

* Add module utilities for db operations

## 1.0.1 ##

* Updated the readme.
* Fixed some issues raised by sanity tests.

## 1.0.0 ##

* Standardize module versions.
* Fix a bug in oracle_user.

## 0.9.0 ##

First release of the collection on Ansible Galaxy.

## 0.8 ##

Initial version, before creating the collection.
