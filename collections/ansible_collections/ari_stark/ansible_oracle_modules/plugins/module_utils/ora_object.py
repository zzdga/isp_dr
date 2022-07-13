# Copyright: (c) 2020, Ari Stark <ari.stark@netcourrier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re


class Size:
    """
    Class to modelize a size clause.

    More information on a size clause here :
    https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/size_clause.html
    """

    size = 0  # Size in bytes
    unlimited = False
    units = ['K', 'M', 'G', 'T', 'P', 'E']

    def __init__(self, size):
        try:  # If it's an int
            self.size = int(size)
        except (ValueError, TypeError):  # Else, try to convert
            if size.lower() == 'unlimited':
                self.unlimited = True

            m = re.compile(r'^(\d+(?:\.\d+)?)([' + ''.join(self.units) + '])$', re.IGNORECASE).match(size)
            if m:
                value = m.group(1)
                unit = m.group(2).upper()
                self.size = int(float(value) * 1024 ** (self.units.index(unit) + 1))

    def __str__(self):
        if self.unlimited:
            return 'unlimited'
        num = self.size
        for unit in [''] + self.units:
            if num % 1024.0 != 0:
                return '%i%s' % (num, unit)
            num /= 1024.0
        return '%i%s' % (num, 'Z')

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return (self.unlimited and other.unlimited or
                self.size == other.size)

    def __lt__(self, other):
        if self.unlimited:
            return False
        elif other.unlimited:
            return True
        elif self.size < other.size:
            return True
        else:
            return False

    def __gt__(self, other):
        if other.unlimited:
            return False
        elif self.unlimited:
            return True
        elif self.size > other.size:
            return True
        else:
            return False


class Datafile:
    """Class to modelize a data file clause."""
    autoextend = None
    maxsize = None
    nextsize = None
    path = None
    size = None
    block_size = None
    max_blocks_for_small_file = 4194302

    def __init__(self, path, size, autoextend=False, nextsize=None, maxsize=None, bigfile=False, block_size=8192):
        self.path = path
        self.size = Size(size) if size else None
        self.autoextend = autoextend
        self.nextsize = Size(nextsize) if nextsize else None
        self.maxsize = Size(maxsize) if maxsize else None
        self.block_size = block_size
        # For a smallfile unlimited is max_blocks * block_size.
        if not bigfile and self.maxsize and self.max_blocks_for_small_file * self.block_size == self.maxsize.size:
            self.maxsize.unlimited = True

    def data_file_clause(self):
        sql = "'%s' %s" % (self.path, self.file_specification_clause())
        return sql

    def file_specification_clause(self):
        sql = "size %s reuse %s" % (self.size, self.autoextend_clause())
        return sql

    def autoextend_clause(self):
        if self.autoextend:
            sql = ' autoextend on'
            if self.nextsize:
                sql += ' next %s' % self.nextsize
            if self.maxsize:
                sql += ' maxsize %s' % self.maxsize
        else:
            sql = ' autoextend off'
        return sql

    def asdict(self):
        _dict = {'path': self.path, 'size': str(self.size), 'autoextend': self.autoextend}
        if self.autoextend:
            if self.nextsize:
                _dict['nextsize'] = str(self.nextsize)
            if self.maxsize:
                _dict['maxsize'] = str(self.maxsize)
        return _dict

    def needs_resize(self, prev):
        """Resize is done only if datafile must be bigger and is not on autoextend"""
        return not self.autoextend and prev.size.__lt__(self.size)

    def needs_change_autoextend(self, prev):
        """Autoextend change when switching from off to on, and conversely, or when it's on and sizes change"""
        has_maxsize_changed = self.autoextend and self.maxsize is not None and not self.maxsize.__eq__(prev.maxsize)
        has_nextsize_changed = self.autoextend and self.nextsize is not None and not self.nextsize.__eq__(prev.nextsize)
        return self.autoextend != prev.autoextend or has_maxsize_changed or has_nextsize_changed


class FileType:
    """Sugar class to manage tablespace file type : smallfile or bigfile."""
    bigfile = None

    def __init__(self, bigfile):
        self.bigfile = bigfile

    def __str__(self):
        return 'bigfile' if self.bigfile else 'smallfile'

    def __eq__(self, other):
        if not isinstance(other, FileType):
            return False
        return self.bigfile == other.bigfile

    def is_bigfile(self):
        return self.bigfile


class ContentType:
    """Sugar class to manage tablespace content type : temp, undo or permanent."""
    content = None

    def __init__(self, content):
        self.content = content

    def __str__(self):
        return self.content

    def __eq__(self, other):
        if not isinstance(other, ContentType):
            return False
        return self.content == other.content

    def create_clause(self):
        map_clause = {'permanent': '', 'undo': 'undo', 'temp': 'temporary'}
        return map_clause[self.content]

    def datafile_clause(self):
        map_clause = {'permanent': 'datafile', 'undo': 'datafile', 'temp': 'tempfile'}
        return map_clause[self.content]
