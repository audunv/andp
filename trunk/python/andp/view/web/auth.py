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

This module renders pages related to user authentication (/login etc.)

"""

import time, urllib

import mod_python.util

from mod_python import apache

import andp.exceptions
import andp.view.web

from andp.view.web import Page, ConfirmationDialog, EH

class CookieTestPage(Page):
    """

    /ctest

    Users who log on are directed to this page first to make sure that
    their browsers actually accept cookies. If not we display an error
    message.
    
    """
    
    path = "/ctest"

    def Main(self):
        if self.user:
            form = mod_python.util.FieldStorage(self.req)
            target = self.GetTarget(form)
            self.Redirect(target)
            return

        html = self.LoadTemplate()

        self.SendHeader()
        self.Write(html)

        return apache.OK

class LoginPage(Page):
    """

    /login
    
    """
    
    path = "/login"

    def Main(self):
        if not self.req.is_https():
            self.RedirectToLogin()

        form = mod_python.util.FieldStorage(self.req)

        target = self.GetTarget(form)

        try:
            username = form["username"].value
        except KeyError:
            username = ""

        try:
            password = form["password"].value
        except KeyError:
            password = ""

        loginMsg = ''

        if username:
            try:
                sessionID = andp.model.users.LogIn(self.req.config, self.req.conn, self.req.cursor, username, password)
            except andp.exceptions.LoginFailed:
                loginMsg = '<span class="error">Login failed. Are you sure you entered the correct user name and password?</span>'
            except andp.exceptions.TooManyLoginAttempts:
                loginMsg = '<span class="error">Too many attempts have been made to log in to your account. Please wait for up to an hour before trying again.</span>'
            else:
                timeout = self.req.config["session"]["timeout"]
            
                cookie = mod_python.Cookie.Cookie("s", sessionID)
                cookie.expires = time.time() + timeout
                cookie.path = "/"
                if self.req.config["web"]["security"] == "SSL":
                    cookie.secure = True
                
                cookie.domain = self.req.config["network"]["host"] + "." + self.req.config["network"]["domain"]

                mod_python.Cookie.add_cookie(self.req, cookie)

                self.Redirect("/ctest?" + urllib.urlencode({"target": target}))
                return

        d = {
            "password": EH(password),
            "username": username,
            "target": target,
            "login_message": loginMsg
            }
            
        self.SendHeader()
        html = self.LoadTemplate()
        self.Write(html % d)
#        self.Write("\n<br>".join(dir(self.req)))
#        self.Write(self.req.ssl_var_lookup("SSL_CIPHER"))

        return apache.OK

class LogoutPage(Page):
    """

    /logout
    
    """
    
    path = "/logout"

    def Main(self):
        sessionID = self.GetSessionID()

        if sessionID:
            self.user.LogOut(self.req.cursor, sessionID)
            
        self.Redirect("/logged_out")

class LoggedOutPage(Page):
    """

    /logged_out
    
    """

    path = "/logged_out"
