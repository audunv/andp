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

This module defines classes, functions and database tables
for remote control functionality

"""

import datetime

# Sessions last for a maximum of SESSION_LENGTH seconds.  When less
# than GRACE_PERIOD seconds are left of session, new QR codes
# etc. will be returned

SESSION_LENGTH = datetime.timedelta(minutes = 10)
GRACE_PERIOD   = datetime.timedelta(minutes = 5)

import andp.exceptions

from andp.db import PsE

def RegisterClient(req, host):
    # Delete all expired sessions
    PsE(req.cursor, "delete from TVSessions where current_timestamp - startTime > %s", (SESSION_LENGTH,))

    # Find youngest 
    PsE(req.cursor, "select min(current_timestamp - startTime) from TVSessions where host=%s", (host,))
    delta = req.cursor.fetchone()[0]

    # Create new session if host is unknown or has entered grace period
    if delta == None or delta > SESSION_LENGTH - GRACE_PERIOD:
        PsE(req.cursor, "insert into TVSessions (host) values (%s)", (host,))

def SessionIDForHost(req, host):
    # Return session ID if available, otherwise None
    
    PsE(req.cursor, "select code from TVSessions where host=%s", (host,))
    #uri = "http://%s.%s/%s" % (req.config["network"]["host"], req.config["network"]["domain"], req.cursor.fetchone()[0])

    try:
        sessionID = req.cursor.fetchone()[0]
    except TypeError:
        sessionID = None

    return sessionID

def HostBySessionID(req, sessionID):
    "Returns host name (or IP) if session is know, otherwise None"
    
    PsE(req.cursor, "select host from TVSessions where code=%s and current_timestamp - startTime < %s", (sessionID, SESSION_LENGTH))
    res = req.cursor.fetchone()

    if res:
        return res[0]
    else:
        return None
    
