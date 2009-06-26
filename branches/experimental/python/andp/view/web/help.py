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

This module renders everything under /library

"""

import pprint, os, stat, re, glob

import mod_python.util

from mod_python import apache

import andp.model.bookings

import andp.view.web
import andp.view.web.widgets

from andp.view.web import Page, Dispatcher, ConfirmationDialog, EH

class Help(Page):
    """

    Library page and subpages

    """

    path = "/help/" #"/library/*"

    def Main(self):

        d = {}
        d["help"] = """
        <h2>VLC</h2>
        <p> This system is designed to be viewed with the <a href="http://www.videolan.org/">VLC</a> player. When you install it on a Windows platform, you will need to check off installing the VLC plugin for ActiveX and Firefox/mozilla. </p>
        <p>For Mac Os X, the VLC plugin is a separate <a href="http://www.videolan.org/vlc/download-macosx.html">download</a> for the plugin, and the player.</p>
        <p>Most linux distributions also maintains the plugin separate from the player, although package names do vary.</p>
        """
        
        html = self.LoadTemplate("main.html")

        self.SendHeader()
        self.Write(html % d)
        return apache.OK
