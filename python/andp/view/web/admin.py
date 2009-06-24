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

This module renders everything under /admin

"""

import mod_python.util

from mod_python import apache

import andp.model.tuners

import andp.model.users

import andp.view.web

from andp.view.web import Page, Dispatcher

class Admin(Page):
    """

    Main admin page
    
    """

    path = "/admin/"

    def ChannelToHTML(self, c):
        """
        
        Returns channel info formatted as HTML
        
        """
        
        return '<tr><td>%s</td><td>%s</td></tr>' % (c.name, c.provider)

    def Main(self):
        if self.user == None or not self.user.admin:
            self.RedirectToLogin()
            return

        numChannels, tunerCounts = andp.model.tuners.CountChannels(self.req.cursor)
        
        html = self.LoadTemplate("main.html")

        d = {}
        d["numChannels"] = numChannels
        d["tuners"] = '<ul>%s</ul>' % "\n".join(["<li>%s: %i channels</li>" % i for i in tunerCounts])
        d["channels"] = '\n'.join([self.ChannelToHTML(c) for c in andp.model.tuners.GetChannels(self.req.cursor, 'e')])

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class AdminAdminsPage(Page):
    path = "/admin/admins"

    def Main(self):
        if self.user == None or not self.user.admin:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)

        if form.has_key('add') and form.has_key("available"):
            andp.model.users.AddAdminAccess(self.req.cursor, form["available"].value)
        elif form.has_key('remove') and form.has_key("enabled"):
            andp.model.users.RemoveAdminAccess(self.req.cursor, form["enabled"].value)
        elif form.has_key('done'):
            self.Redirect("./")

        html = self.LoadTemplate("select_channels.html")

        d = {}
        d["title"] = "Manage administrators"
        d["message"] = "Select which users should have admin access."
        d["available"] = "\n".join(['  <option value="%s">%s (%s)</option>' % (c[3], c[0], c[1]) for c in andp.model.users.GetUsers(self.req.cursor, "fullName", True, 'users')])
        d["enabled"] = "\n".join(['  <option value="%s">%s (%s)</option>' % (c[3], c[0], c[1]) for c in andp.model.users.GetUsers(self.req.cursor, "fullName", True, 'admins')])

        self.SendHeader()
        self.Write(html % d)
        return apache.OK



        if form.has_key("addadmin"):
            andp.model.users.AddAdminAccess(self.req.cursor, form["addadmin"])
            d["message"] = "Admin rights successfully added to %s" % form["addadmin"]
        if form.has_key("removeadmin"):
            andp.model.users.RemoveAdminAccess(self.req.cursor, form["removeadmin"])
            d["message"] = "Admin rights successfully removed from %s" % form["removeadmin"]




class AdminUsersPage(Page):
    path = "/admin/users"

    def UsersToHTML(self, c):
        """                                                                     
                                                                               
        Returns user info formatted as HTML                                  
                                                                                
        """
        
        name, email, admin, username = c

        if admin:
            admin = "<img src='/img/can.gif' alt='X' />"
        else:
            admin = ""

        return '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (name, username, email, admin)


    def Main(self):
        if self.user == None or not self.user.admin:
            self.RedirectToLogin()
            return

        self.SendHeader()

        form = mod_python.util.FieldStorage(self.req)

        html = self.LoadTemplate("userlist.html")

        d = {}
        d["message"] = ""
        d["order"] = "asc"
        order = True

        if form.has_key("sort"):
            col = form["sort"]
        else:
            col = "fullName"

        if form.has_key("order"):
            if form["order"] == "asc":
                d["order"] = "desc"
                order = False
            else:
                order = True
                d["order"] = "asc"

        d["users"] = "\n".join([self.UsersToHTML(c) for c in andp.model.users.GetUsers(self.req.cursor, col, order)])

        self.Write(html % d)
        return apache.OK

class AdminTunersUpdateChannelLists(Page):
    path = "/admin/tuners/update_channel_lists"

    def Main(self):
        if self.user == None or not self.user.admin:
            self.RedirectToLogin()
            return

        andp.model.tuners.UpdateChannelLists(self.req.cursor, [h[:2] for h in self.req.config["tuners"]["hosts"]])

        self.SendHeader()
        self.WriteMessage("Channel lists updated", "The channels lists have been successfully updated", "../")
        return apache.OK

class AdminSelectChannels(Page):
    path = "/admin/select_channels"

    def Main(self):
        if self.user == None or not self.user.admin:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)

        if form.has_key('add') and form.has_key("available"):
            andp.model.tuners.EnableChannel(self.req.cursor, form["available"].value)
        elif form.has_key('remove') and form.has_key("enabled"):
            andp.model.tuners.DisableChannel(self.req.cursor, form["enabled"].value)
        elif form.has_key('done'):
            self.Redirect("./")

        html = self.LoadTemplate()

        d = {}
        d["message"] = "Select which channels should be available to your users."
        d["title"] = "Select channels"
        d["available"] = "\n".join(['  <option value="%s">%s (%s)</option>' % (c.id, c.name, c.provider) for c in andp.model.tuners.GetChannels(self.req.cursor, 'd', 's')])
        d["enabled"] = "\n".join(['  <option value="%s">%s (%s)</option>' % (c.id, c.name, c.provider) for c in andp.model.tuners.GetChannels(self.req.cursor, 'e', 's')])

        self.SendHeader()
        self.Write(html % d)
        return apache.OK
