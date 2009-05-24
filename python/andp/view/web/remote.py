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

This module handles the remote control interface

"""

import subprocess

from mod_python import apache

import andp.model.remote

from andp.view.web import Page

class RemoteQR(Page):
    """

    Returns a QR code image, and records the client's address for
    remote-control callbacks
    
    """
    
    path = "/remote/qr"
    showDebug = False

    def Main(self):
        host = self.req.get_remote_host(apache.REMOTE_NOLOOKUP)

        andp.model.remote.RegisterClient(self.req, host)
        sessionID = andp.model.remote.SessionIDForHost(self.req, host)

        cmd = ("qrencode", "-s", "16", "-m", "0", "-o", "-")
        proc = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE)

        uri = "http://%s.%s/%s" % (self.req.config["network"]["host"], self.req.config["network"]["domain"], sessionID)
        img = proc.communicate(uri)[0]
        
        self.SendHeader(contentType = "image/png")
        self.Write(img)
        
        return apache.OK

class RemoteRemote(Page):
    """

    Displays remote-control UI
    
    """

    path = None # Hard-coded in handler.py :-/

    def Main(self):
        sessionID = self.req.uri[1:5]

        host = andp.model.remote.HostBySessionID(self.req, sessionID)
        if not host:
            return apache.HTTP_NOT_FOUND
        
        self.SendHeader()
        self.Write("foo")

        return apache.OK
