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

import time, sys, re

import psycopg2

import mod_python.Cookie

from mod_python import apache

import andp.config
import andp.view.web

from andp.view.web.auth     import *
from andp.view.web.bookings import *
from andp.view.web.library  import *
from andp.view.web.admin    import *
from andp.view.web.help     import *
from andp.view.web.remote   import *

# cfg depends on the configuration path, which won't be known before
# we receive our first request.
cfg = None

dbConnection = None

REMOTE_PATTERN = re.compile(r'^/[a-z0-9]{4}$')

def handler(req):
    remoteHost = req.get_remote_host(apache.REMOTE_NOLOOKUP)
    #if remoteHost not in ("158.39.165.66", "81.175.13.7", "158.39.165.133"):
    #    return 403
    
    global cfg, dbConnection
    
    req.debugThen = time.time()

    if cfg == None:
        cfgPath = req.get_options()["andpConfigPath"]
        
        cfg = andp.config.Load(cfgPath)

    dbName = cfg["database"]["name"]
    dbUser = cfg["database"]["webUser"]

    hostName = "%s.%s" % (cfg["network"]["host"], cfg["network"]["domain"])
    if req.hostname != hostName:
        # *** Todo: Handle other protocols (e.g. HTTPS) and ports
        target = "http://%s%s" % (hostName, req.uri)
        mod_python.util.redirect(req, target)
        return

    if not dbConnection:
        dbConnection = psycopg2.connect("dbname=%s user=%s" % (dbName, dbUser))

    req.config = cfg
    req.conn = dbConnection
    req.cursor = dbConnection.cursor()

    if pathMapping.has_key(req.uri):
        try:
            res = pathMapping[req.uri](req)()
        except:
            req.conn.rollback()
            raise
        else:
            req.conn.commit()
            return res
    elif req.uri.startswith("/m3u/"):
        try:
            res = M3U(req)()
        except:
            req.conn.rollback()
            raise
        else:
            req.conn.commit()
            return res
    elif req.uri.startswith("/library2/"):
        try:
            res = Library2(req)()
        except:
            req.conn.rollback()
            raise
        else:
            req.conn.commit()
            return res
    elif REMOTE_PATTERN.search(req.uri):
        try:
            res = RemoteRemote(req)()
        except:
            req.conn.rollback()
            raise
        else:
            req.conn.commit()
            return res
    else:
        return apache.HTTP_NOT_FOUND

pathMapping = dict([(c.path, c) for c in globals().values() if type(c) is type and issubclass(c, Page) and c is not Page and isinstance(c.path, str)])
