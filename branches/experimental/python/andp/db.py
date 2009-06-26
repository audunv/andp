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

This module contains various utility functions for connecting to Postgres.

IMPORTANT:

  * NEVER INCLUDE ARGUMENTS IN SQL STATEMENT ITSELF. USE args INSTEAD,
    THUS PROTECTING US AGAINST SQL INJECTION ATTACKS.

  * ALWAYS USE THE PsE FUNCTION WHEN EXECUTING SQL STATEMENTS. IT
    ENSURES THAT EXCEPTIONS ARE APPROPRIATELY CAUGHT.

"""

import os, re
import psycopg2
import andp.exceptions

P_LOGIN_FAILED       = re.compile(r'^ERROR: *andp: login failed')
P_TOO_MANY_LOGINS    = re.compile(r'^ERROR: *andp: too many login attempts')
P_NOT_FOUND          = re.compile(r'^ERROR: *andp: not found')

P_NO_SUCH_DATABASE   = re.compile(r'^ERROR: *database .*? does not exist')
P_SYNTAX_ERROR       = re.compile(r'^ERROR: *syntax error at or near')
P_FUNCTION_NOT_FOUND = re.compile(r'^ERROR: *function .*? does not exist')

def PsE(cursor, cmd, args = None):
    """
    Executes an SQL command just like cursor.execute, but tries to
    handle exceptions a bit more intelligently.

      * cursor: Postgres cursor

      * cmd: SQL command

      * args: SQL arguments

    """
    
    try:
        if args == None:
            cursor.execute(cmd)
        else:
            cursor.execute(cmd, args)

    except psycopg2.ProgrammingError, info:
        s = info.args[0]

        if   P_LOGIN_FAILED.search(s):
            raise andp.exceptions.LoginFailed, info
        elif P_TOO_MANY_LOGINS.search(s):
            raise andp.exceptions.TooManyLoginAttempts, info
        elif P_NOT_FOUND.search(s):
            raise andp.exceptions.NotFound, info

        elif P_NO_SUCH_DATABASE.search(s):
            raise andp.exceptions.NoSuchDatabaseError, info
        elif P_SYNTAX_ERROR.search(s):
            raise andp.exceptions.SQLSyntaxError, info
        elif P_FUNCTION_NOT_FOUND.search(s):
            raise andp.exceptions.SQLFunctionNotFoundError, info
        else:
            raise
