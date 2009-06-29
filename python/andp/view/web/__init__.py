#! /usr/bin/python
# -*- coding: iso-8859-1; -*-

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

This package contains classes and functions used to render the web
interface

"""

__all__ = ["auth", "bookings", "library", "admin", "widgets", "remote", "browse"]

import re, os, time, urllib, socket

import mod_python.util
import mod_python.Cookie

from mod_python import apache

import andp.exceptions

import andp.model.users

def EH(html):
    """
    Escapes <, >, & and \" in HTML strings

    Should always be used when outputting any user-originated data to
    HTML (to avoid cross-site scripting attacks etc.)
    """

    return html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

class Page(object):
    """

    Base class for all web interface pages
    
    """
    
    showDebug = True # Show debug info (performance) if showDebug is True and debug mode is on

    # Used for parsing HTML template files
    reTitle = re.compile(r'<title>(.*?)</title>', re.DOTALL)
    reBody  = re.compile(r'<body>(.*)</body>', re.DOTALL)

    def __init__(self, req):
        """

          * req: req object from mod_python
        
        """
        
        super(Page, self).__init__()

        self.req = req

        self.htmlRoot = self.req.config["path"]["html"]

        self.title = None
        
        self.user = self.GetUser()

    def GetPath(self):
        """

        Returns page's path on web server.

        Override this for pages that use regexp paths.
        
        """

        return self.path

    def GetFSPath(self):
        """

        Returns page's template path (relative to template root)
        
        """

        return self.path[1:] + ".html"

    def GetTarget(self, form, default = "/"):
        """
        
        Returns either the value of the "target" CGI parameter, or the
        value of the HTTP referer variable. If e ither is unsafe,
        default is returned (default value: /).

        Useful for pages that need to keep track of which page the
        user came from (for redirection).

          * form: Form object

          * default: Default default value :-) (default: /)
          
        """

        try:
            target = form["target"].value
        except KeyError:
            try:
                target = "/" + self.req.headers_in["referer"].split("/", 3)[-1]
            except KeyError:
                target = default

        if not self.SafeTarget(target):
            target = default

        return target

    def SafeTarget(self, target):
        """

        Return True if target is a safe URL, i.e. a URL that points to
        a path on our web server, and not to an external URL. Use to
        avoid XSS exploits.

        """
        
        if ":" in target:
            return False
        else:
            return True

    def SetCacheHeaders(self):
        """

        Sets appropriate caching parameters (especially important for
        IE)
        
        """

        # Most pages are dynamic and user-specific and should
        # therefore not be cached
        self.req.headers_out["Cache-Control"] = "no-cache"
        self.req.headers_out["Pragma"] = "no-cache"
        self.req.headers_out["Expires"] = "-1"

    def SendHeader(self, contentType = "text/html; charset=utf-8"):
        """

        Sets content-type and sends HTTP header
        
        """

        self.SetCacheHeaders()

        self.req.content_type = contentType
        self.req.send_http_header()

    def GetHTMLHead(self):
        """
        Returns page-specific HTML head as a string
        """

        return ""

    def GetDetailsHTML(self, booking):
        owner = andp.model.users.GetUserByUsername(self.req.cursor, booking.username)

        sTime = booking.startTime.strftime('%d %B %Y, %H:%M:%S')
        eTime = booking.endTime.strftime('%d %B %Y, %H:%M:%S')
        ownerS = '<a href="mailto:%s">%s</a>' % (owner.email, EH(owner.fullName))
        
        return '<p><strong>Start:</strong> %s&nbsp;&nbsp;&nbsp;<strong>End:</strong> %s&nbsp;&nbsp;&nbsp;<strong>Owner:</strong> %s</p>' % (sTime, eTime, ownerS)

    def GetPreviewHTML(self, booking):
        try:
            isIE = "msie" in self.req.headers_in["User-Agent"].lower()
        except KeyError:
            isIE = False

        if isIE:
            return self.GetPreviewHTMLIE(booking)
        else:
            return self.GetPreviewHTMLMozilla(booking)

    def GetPreviewHTMLMozilla(self, booking):
        html  = '<p>\n'

        # Only allow pausing for on-demand streams
        if booking.state == 'f':
            html += '  <input onClick="document.vlc.play(); document.getElementById(\'btnPlay\').style.display = \'none\'; document.getElementById(\'btnPause\').style.display = \'inline\';" type="button" value="Play" style="display: none;" id="btnPlay" />\n'
            html += '  <input onClick="document.vlc.pause(); document.getElementById(\'btnPlay\').style.display = \'inline\'; document.getElementById(\'btnPause\').style.display = \'none\';" type="button" value="Pause" id="btnPause" />\n'

        html += '  <input onClick="vlc.fullscreen()" type="button" value="Full-screen" />\n'
        html += '  (double-click to exit full-screen mode)\n'
        html += '</p>\n'
        html += '<embed type="application/x-vlc-plugin" name="vlc" autoplay="yes" loop="no" width="1024" height="576" target="http://%s.%s/m3u/%s.m3u" />' % (self.req.config["network"]["host"], self.req.config["network"]["domain"], booking.id)

        return html

    def GetPreviewHTMLIE(self, booking):
        html  = '<p>\n'

        # Only allow pausing for on-demand streams
        if booking.state == 'f':
            html += '  <input onClick="vlc.play(); btnPlay.style.display = \'none\'; btnPause.style.display = \'inline\';" type="button" value="Play" style="display: none;" id="btnPlay" />\n'
            html += '  <input onClick="vlc.pause(); btnPlay.style.display = \'inline\'; btnPause.style.display = \'none\';" type="button" value="Pause" id="btnPause" />\n'

        html += '  <input onClick="vlc.fullscreen()" type="button" value="Full-screen" />\n'
        html += '  (double-click to exit full-screen mode)\n'
        html += '</p>\n'
        html += '<object classid="clsid:E23FE9C6-778E-49D4-B537-38FCDE4887D8"\n'
        html += '    codebase="http://downloads.videolan.org/pub/videolan/vlc/latest/win32/axvlc.cab"\n'
        html += '    width="1024" height="576" id="vlc" events="True" class="preview">\n'
        html += '  <param name="Src" value="http://%s.%s/m3u/%s.m3u" />\n' % (self.req.config["network"]["host"], self.req.config["network"]["domain"], booking.id)
        html += '  <param name="ShowDisplay" value="True" />\n'
        html += '  <param name="AutoLoop" value="False" />\n'
        html += '  <param name="AutoPlay" value="True" />\n'
        html += '  <param name="Volume" value="100">\n'
        html += '</object>\n'

        return html

    def BookingToHTMLRow(self, booking, restrict = None):
        """

        Returns booking formatted as an HTML table row
        
          booking: Booking object

        Note: Booking is expected to contain a channel attribute
        containing a Channel object
    
        """

        cName = "%s" % (EH(booking.channel.name),)
        sTime = booking.startTime.strftime('%H:%M')
        eTime = booking.endTime.strftime('%H:%M')
        sDate = booking.startTime.strftime('%d %b %Y')

        owner = andp.model.users.GetUserByUsername(self.req.cursor, booking.username)
        
        if booking.record:
            bType = "Broadcast & record"
        else:
            bType = "Broadcast"

        if booking.title:
            title = EH(booking.title)
        else:
            title = '<em>No title</em>'

        if booking.state == "w" and booking.username == self.user.username:
            buttons = '<input type="submit" name="edit_%s" value="Edit..." /><input type="submit" name="delete_%s" value="Delete..." />' % (booking.id, booking.id)
        elif booking.state == "i":
            tuner = andp.model.tuners.GetTuner(self.req.cursor, self.req.config, booking.tunerID)
            buttons = '<input type="submit" name="watch_%s" value="Watch..." />' % booking.id
        elif booking.state == "f":
            buttons = '<input type="submit" name="watch_%s" value="Watch..." />' % booking.id
            if booking.username == self.user.username:
                buttons += '<input type="submit" name="delete_%s" value="Delete..." />' % booking.id
        elif booking.state == 'e':
            buttons = '<input type="submit" name="errinfo_%s" value="Error info..." />' % booking.id
        else:
            buttons = ""
            
        return '      <tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="mailto:%s">%s</a></td><td>%s</td></tr>' % (title, cName, sTime, eTime, sDate, bType, owner.email, owner.fullName, buttons)

    def BookingsToHTML(self, bookings, sortColumn = "date", sortDir = "desc"):
        """

        Returns list of Booking objects formatted as an HTML table inside
        an HTML form.

          bookings: List of Booking objects

        Note: Each Booking is expected to contain a channel attribute
        containing a Channel object
    
        """
        # SQL injection countermeasure as well as explisite if
        if sortDir == "asc":
            sortDir = "desc"
            sortArrow = "&#9650;"
        else:
            sortDir = "asc"
            sortArrow = "&#9660;"
            
        templateSort = '<a href="?sort=%s&sortDir=%s&sortColumn=%s">%s%s</a>'
        # SQL injection countermeasure and explisite if

        assert sortColumn in ["owner", "date", "title", "channel"]

        if sortColumn == "owner":
            sortOwner = templateSort % ("owner", sortDir, "owner", "Owner", sortArrow)
        else:
            sortOwner = templateSort % ("owner", sortDir, "owner", "Owner", "")

        if sortColumn == "title":
            sortTitle = templateSort % ("title", sortDir, "title" , "Title", sortArrow)
        else:
            sortTitle = templateSort % ("title", sortDir, "title", "Title", "")

        if sortColumn == "channel":
            sortChannel = templateSort % ("channel", sortDir, "channel", "Channel", sortArrow)
        else:
            sortChannel = templateSort % ("channel", sortDir, "channel", "Channel", "")

        if sortColumn == "date":
            sortDate = templateSort % ("date", sortDir, "date", "Date", sortArrow)
        else:
            sortDate = templateSort % ("date", sortDir, "date", "Date", "")

        html  = '<form action="dispatch" method="get">\n'
        html += '  <table>\n'
        html += '    <tr>\n'
        html += '      <th>%s</th><th>%s</th><th>Start</th><th>End</th><th>%s</th><th>Type</th><th>%s</th>\n' % (sortTitle, sortChannel, sortDate, sortOwner)
        html += '\n'.join([self.BookingToHTMLRow(b) for b in bookings])
        html += '    </tr>\n'
        html += '  </table>\n'
        html += '<form>\n'
        
        return html

    def BrowseBookingsToHTML(self, numParams, params, sortDir = "desc"):
        """

        Returns list of Booking objects formatted as an HTML table inside
        an HTML form.

          bookings: List of Booking objects

        Note: Each Booking is expected to contain a channel attribute
        containing a Channel object
    
        """
        if sortDir == "asc":
            sortDir = "desc"
            sortArrow = "&#9650;"
        else:
            sortDir = "asc"
            sortArrow = "&#9660;"

        years = andp.model.bookings.GetYearsWithRecordings(self.req.cursor)
        if params["year"] != None:
            months = andp.model.bookings.GetMonthsWithRecordings(self.req.cursor, params["year"])
            bookings = andp.model.bookings.GetBookingsByInterval(self.req.cursor, "%s-01-01" % (params["year"]), andp.model.bookings.YEAR)
        else:
            bookings = andp.model.bookings.GetBookings(self.req.cursor)

        if params["month"] != None:
            days = andp.model.bookings.GetDaysWithRecordings(self.req.cursor, params["year"], params["month"])
            bookings = andp.model.bookings.GetBookingsByInterval(self.req.cursor, "%s-%s-01" % (params["year"], params["month"]), andp.model.bookings.MONTH)

        if params["day"] != None:
            bookings = andp.model.bookings.GetBookingsByInterval(self.req.cursor, "%s-%s-%s" % (params["year"], params["month"], params["day"]), andp.model.bookings.DAY)

        html = ""
        
        html += '   <div id="browseupperleft">'
        for counter in range(0, numParams+1):
            html += '  <div class="browseleft">'
            html += '  <table>\n'
            html += '    <tr>\n'
            if counter == 0:
                html += '\n'.join([self.BrowseBookingToHTMLRow(y, "year", params) for y in years])
            if counter == 1:
                html += '\n'.join([self.BrowseBookingToHTMLRow(m, "month", params) for m in months])
            if counter == 2:
                html += '\n'.join([self.BrowseBookingToHTMLRow(d, "day", params) for d in days])
            html += '    </tr>\n'
            html += '  </table>\n'
            html += ' </div>'
        html += '   </div>'


        html += '<div id="browseupperright">'
        html += ' <form action="/library/dispatch" method="get">\n'
        html += '  <div class="browseleft">'
        html += '  <table>\n'
        html += '    <tr>\n'
        html += '\n'.join([self.BookingToHTMLRow(b) for b in bookings])
        html += '    </tr>\n'
        html += '  </table>\n'
        html += ' </div>'
        html += ' <form>\n'
        html += '</div>\n'
        html += '<div id="browselower">\n'
        html += '&nbsp;'
        html += '</div>'
        
        return html

    def BrowseBookingToHTMLRow(self, data, column, params):
        """

        """

        if column == "year":
            data = "%s" % data
            if data == params["year"]:
                selected = ' class="browseselected"'
            else:
                selected = ""
            return '      <tr%s><td><a href="/library2/%s/">%s</a></td></tr>' % (selected, data, data)

        elif column == "month":
            data = "%s" % data
            if data == params["month"]:
                selected = ' class="browseselected"'
            else:
                selected = ""
            return '      <tr%s><td><a href="/library2/%s/%s/">%s</a></td></tr>' % (selected, params["year"], data, data)

        elif column == "day":
            data = "%s" % data
            if data == params["day"]:
                selected = " class=browseselected"
            else:
                selected = ""
            return '      <tr><td%s><a href="/library2/%s/%s/%s/">%s</a></td></tr>' % (selected, params["year"], params["month"], data, data)
        elif column == "channel":
            return '      <tr><td><a href="/library2/%s/">%s</a></td></tr>' % (data.id, data.name)
        else:
            return "Nothing!"

    def __call__(self):
        """

        Should normally not be overriden by subclasses

        """
        
        res = self.Main()

        if self.showDebug and self.req.config["debug"]["debugMode"]:
            elapsed = time.time() - self.req.debugThen
            self.Write("\n\n<!-- %f (%i) -->" % (elapsed, 1 / elapsed))

        return res

    def Main(self):
        """

        Override this to provide other functionality
        
        """
        
        self.SendHeader()
        html = self.LoadTemplate()

        self.Write(html)
        return apache.OK

    def ValidateInput(self, widgets, form):
        """

        Returns True if all widgets contain valid data from form

        """
        
        res = [widget.ParseInput(form)[0] for widget in widgets.values()]

        if False in res:
            return False
        else:
            return True

    def GetSessionID(self):
        """
        
        Returns session ID (from a user's cookie info),
        or None if not found.

        IMPORTANT: Session IDs should never be trusted.
        
        """

        cookies = mod_python.Cookie.get_cookies(self.req)

        try:
            sessionID = cookies["s"].value
        except KeyError:
            sessionID = None

        return sessionID

    def GetUser(self):
        """
        
        Returns None if user is unauthorized
        
        """
        
        sessionID = self.GetSessionID()

        if sessionID == None:
            return None

        user = andp.model.users.GetUser(self.req.cursor, sessionID)

        return user

    def RedirectToLogin(self):
        """

        Redirects to login page in a way that lets it redirect back to
        this page again.
        
        """

        if self.req.config["web"]["security"] == "SSL":
            url = "https://" + self.req.config["network"]["host"] + "." + self.req.config["network"]["domain"] + "/login?" + urllib.urlencode({"target": self.GetPath()})
        else:
            url = "/login?" + urllib.urlencode({"target": self.GetPath()})
        
        time.sleep(0.1)

        self.SendHeader()
        
        permanent = False

        # We need to commit our cursor here, since                              
        # mod_python.util.redirect will make handler.py skip the                
        # commmit step                                                          
        self.req.conn.commit()

        mod_python.util.redirect(self.req, url, permanent)


    def LoadTemplate(self, fName = None):
        """

        Loads page template from file. Renders and caches parts that
        don't vary between requests.

          * fName: Optional template name. Defaults to class.GetFSPath()
        
        """
        
        if fName:
            pathPart = os.path.split(self.GetFSPath())[0]
            fsPath = os.path.join(self.htmlRoot, pathPart, fName)
        else:
            fsPath = os.path.join(self.htmlRoot, self.GetFSPath())

        html = open(fsPath).read()

        title = self.reTitle.findall(html)[0]
        body  = self.reBody.findall(html)[0]

        templatePath = os.path.join(self.htmlRoot, "generic", "template.html")

        template = open(templatePath).read()

        # To indicate active tab
        cur = ' id="current"'

        d = {"title": title, "body": body}

        d["tab_bookings"] = ""
        d["tab_library"] = ""
        d["tab_help"] = ""
        d["tab_browse"] = ""

        if self.user and self.user.admin:
            d["tab_admin"] = ' style="display: block;"'
        else:
            d["tab_admin"] = ' style="display: none;"'

        #if self.req.uri.startswith("/"):
        #    d["tab_bookings"] = cur
        if self.req.uri.startswith("/library2/"):
            d["tab_library"] = cur
        elif self.req.uri.startswith("/admin/"):
            d["tab_admin"] += cur
        elif self.req.uri.startswith("/help/"):
            d["tab_help"] += cur
        elif self.req.uri.startswith("/browse/"):
            d["tab_browse"] += cur
        else:
            d["tab_bookings"] = cur

        # Ensure /admin always points to https
        d["hostname"] = self.req.config["network"]["host"] + "." + self.req.config["network"]["domain"]
    
        if self.user:
            d["userInfo"] = 'You are logged in as %s. <a href="/logout">Log out</a>' % self.user.fullName
        else:
            d["userInfo"] = ''

        d["head"] = self.GetHTMLHead()

        if self.req.config["web"]["security"] == "SSL":
            d["ssl"] = "s"
        else:
            d["ssl"] = ""

        html = template % d
            
        return html

    def Write(self, s):
        """

        Equivalent to self.req.write(s)

        """

        self.req.write(s)

    def Redirect(self, target, permanent = False):
        """

        Redirects to target, making sure that target is safe

        """

        # We'll try this and see if it stops Safari from popping up
        # redundant POST warnings
        time.sleep(0.1)

        assert self.SafeTarget(target)

        self.SendHeader()

        # We need to commit our cursor here, since
        # mod_python.util.redirect will make handler.py skip the
        # commmit step
        self.req.conn.commit()

        mod_python.util.redirect(self.req, target, permanent)

    def WriteMessage(self, title, message, target):
        """

        Outputs a message to user

          * title: Title of message

          * message: Body of message

          * target: Where user is sent after clicking OK button
        
        """
        
        d = {
            "title":   title,
            "message": message,
            "target":  target
            }
        
        fsPath = os.path.join(self.htmlRoot, "generic", "message.html")
        
        self.SendHeader()
        self.Write(self.LoadTemplate(fsPath) % d)
        return apache.OK
    
class ConfirmationDialog(Page):
    """

    Abstract base class for confirmation dialogs
    
    """
    
    path = None

    def __init__(self, req):
        super(ConfirmationDialog, self).__init__(req)

        self.title    = None
        self.message  = None
        self.labelYes = "Yes"
        self.labelNo  = "No"

        self.hiddenName  = None
        self.hiddenValue = None

        self.form = mod_python.util.FieldStorage(self.req)

        self.SetVariables()

    def SetVariables(self):
        """
        
        Subclasses should use this method to initialize variables etc.
        
        """

        pass

    def Process(self):
        """
        
        Performs work that should be done *after*
        initialization.

        NOTE: Method is only called when user hasn't clicked a button
        yet.

        (The order in which in things are done is important. If your
        class doesn't work, try to move as much processing as possible
        into this method.)
        
        """

        pass

    def HandleYes(self):
        """
        
        This method is called if user clicks the Yes (or equivalent) button.
        Must perform a redirect.
        Returns nothing.
        
        """

        self.Redirect(self.GetTarget(self.form))

    def HandleNo(self):
        """
        
        This method is called if user clicks the No (or equivalent) button.
        Must perform a redirect.
        Returns nothing.
        
        """

        self.Redirect(self.GetTarget(self.form))

    def Main(self):
        try:
            self.hiddenValue = self.form[self.hiddenName].value
        except KeyError:
            self.hiddenValue = ""

        self.Process()

        if self.form.has_key('yes') or self.form.has_key('yes.x'):
            self.HandleYes()
        elif self.form.has_key('no') or self.form.has_key('no.x'):
            self.HandleNo()
        else:
            fsPath = os.path.join(self.htmlRoot, "generic", "confirmation.html")

            html = self.LoadTemplate(fsPath)

            d = {
                "title": self.title,
                "message": self.message,
                "yes": self.labelYes,
                "no": self.labelNo,
                "hidden_name": self.hiddenName,
                "hidden_value": self.hiddenValue,
                "target": self.GetTarget(self.form),
                "path": self.GetPath()
                }

            self.SendHeader()
            self.Write(html % d)

            return apache.OK        

class Dispatcher(Page):
    """
    
    Utility class. Useful for forms with more than one submit button.

    """
    
    path = None

    argumentName = None
    actions      = []
    default      = "."

    def GoAway(self):
        self.Redirect(self.default)
        
    def Main(self):
        self.SendHeader("text/plain; charset=utf-8")

        form = mod_python.util.FieldStorage(self.req)

        try:
            name = form.keys()[0]
        except IndexError:
            return self.GoAway()

        parts = name.split("_")
        if len(parts) == 1:
            action = parts[0]
            arg    = None
        elif len(parts) == 2:
            action = parts[0]
            arg    = parts[1]
        else:
            return self.GoAway()

        if action in self.actions:
            if arg:
                url = "%s?%s" % (action, urllib.urlencode({self.argumentName: arg}))
            else:
                url = "%s" % action

            self.Redirect(url)
        else:
            return self.GoAway()
