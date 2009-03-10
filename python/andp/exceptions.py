#! /usr/bin/python
# -*- coding: utf-8; -*-

# Copyright (C) 2009 Østfold University College
# 
# This file is part of ANDP.
# 
# ANDP is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

"""

This module contains exceptions to supplement Python's and Psycopg's
standard repertoire

"""

class Error(Exception):
    pass

class ANDPError(Exception):
    # Errors specific to ANDP
    pass

class DBError(Exception):
    # Errors produced by Postgres itself
    pass

class NoSuchDatabaseError(DBError):
    pass

class SQLSyntaxError(DBError):
    pass

class SQLFunctionNotFoundError(DBError):
    pass

class LoginFailed(ANDPError):
    pass

class TooManyLoginAttempts(ANDPError):
    pass

class InvalidUser(ANDPError):
    pass

class DuplicateKey(ANDPError):
    pass

class NotFound(ANDPError):
    pass

class InvalidTime(ANDPError):
    "Invalid time or date (e.g. Feb 31, or in the past)"
    pass

class InvalidDuration(ANDPError):
    "Booking is too long"
    pass

class NoTunersAvailable(ANDPError):
    "No tuners were available for booking"
    pass

class NoLongerEditable(ANDPError):
    "Booking is no longer editable"
    pass

class NotDeletable(ANDPError):
    "Booking is not currently deletable"
    pass

class TuningError(ANDPError):
    "Unable to tune channel"
    pass
