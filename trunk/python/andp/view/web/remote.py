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

import subprocess, cStringIO

from PIL import Image, ImageDraw, ImageFont

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
    fontPath = "/usr/share/fonts/truetype/ttf-bitstream-vera/Vera.ttf" # Quite randomly chosen

    def Main(self):
        host = self.req.get_remote_host(apache.REMOTE_NOLOOKUP)

        andp.model.remote.RegisterClient(self.req, host)
        sessionID = andp.model.remote.SessionIDForHost(self.req, host)

        cmd = ("qrencode", "-s", "16", "-m", "0", "-o", "-")
        proc = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE)

        uri = "http://%s.%s/%s" % (self.req.config["network"]["host"], self.req.config["network"]["domain"], sessionID)
        buf = cStringIO.StringIO(proc.communicate(uri)[0])
        qrImage = Image.open(buf)

        font = ImageFont.truetype(self.fontPath, 256) # Big enough to scale image down well

        topText = "%s.%s/" % (self.req.config["network"]["host"], self.req.config["network"]["domain"])
        topImage = Image.new("RGB", font.getsize(topText), (0, 0, 0))
        topDraw = ImageDraw.Draw(topImage)
        topDraw.text((0, 0), topText, font = font)
        del topDraw
        topImage = topImage.resize((qrImage.size[0], (float(qrImage.size[0]) / topImage.size[0]) * topImage.size[1]), Image.ANTIALIAS)

        bottomText = "%s" % (sessionID,)
        bottomImage = Image.new("RGB", font.getsize(bottomText), (0, 0, 0))
        bottomDraw = ImageDraw.Draw(bottomImage)
        bottomDraw.text((0, 0), bottomText, font = font)
        del bottomDraw
        bottomImage = bottomImage.resize((qrImage.size[0], (float(qrImage.size[0]) / bottomImage.size[0]) * bottomImage.size[1]), Image.ANTIALIAS)

        compositeImage = Image.new("RGB", (qrImage.size[0], topImage.size[1] + qrImage.size[1] + bottomImage.size[1]), (0, 0, 0))
        compositeImage.paste(topImage, (0, 0))
        compositeImage.paste(qrImage, (0, topImage.size[1]))
        compositeImage.paste(bottomImage, (0, topImage.size[1] + qrImage.size[1]))

        buf = cStringIO.StringIO()
        compositeImage.save(buf, "PNG")
        
        self.SendHeader(contentType = "image/png")
        self.Write(buf.getvalue())
        
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
