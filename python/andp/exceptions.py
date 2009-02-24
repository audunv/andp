#! /usr/bin/python
# -*- coding: utf-8; -*-

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
