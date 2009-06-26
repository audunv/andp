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

class LibraryDispatch(Dispatcher):
    path = "/library/dispatch"

    argumentName = "bID"
    actions      = ["watch", "delete", "errinfo"]

    default = "watch"

class LibraryDelete(ConfirmationDialog):
    """

    /library/delete
    
    """

    path = "/library/delete"

    def SetVariables(self):
        self.title      = "Delete recording?"
        self.message    = '<p>Are you sure you want to permanently delete this recording?</p>'
        self.hiddenName = "bID"
        
        self.labelYes = "Delete recording"
        self.labelNo  = "Cancel"

    def HandleNo(self):
        self.Redirect("./")

    def HandleYes(self):
        booking = andp.model.bookings.GetBooking(self.req.cursor, self.hiddenValue)

        try:
            booking.Delete(self.req.cursor, self.req.config, self.user.username)
        except andp.exceptions.NotDeletable:
            # We should display an error message, but WriteMessage
            # doesn't work here
            pass

        self.Redirect("./")

class M3U(Page):
    """

    Special page for generating M3U files
    
    """

    # Don't need it since it's hard-coded into handler.py. (Not
    # pretty, but functional.)
    path = None

    showDebug = False

    BOOKING_ID = re.compile(r'/m3u/([0-9a-f]{32})\.m3u')
    
    def Main(self):
        browse = False

        m = self.BOOKING_ID.search(self.req.uri)

        if not m:
            # Invalid URL
            nameList = []
            for item in andp.model.tuners.GetChannels(self.req.cursor, 'e', 'i'):
                nameList.append(item.name)
            if self.req.uri.replace("/m3u/", "").replace(".m3u", "") not in nameList:
                return apache.HTTP_NOT_FOUND
            else:
                browse = True
                name = self.req.uri.replace("/m3u/", "").replace(".m3u", "")
                title = name
                booking = andp.model.bookings.FakeBooking()
                booking.channel = andp.model.tuners.IPChannel(None, name)
                startTimeS = name

        if not browse:
            bookingID = m.group(1)
            booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

            if booking.title:
                title = booking.title
            else:
                title = 'Untitled'

            startTimeS = booking.startTime.strftime("%d %B %Y, %H:%M:%S")

            if not booking:
                # Booking does not exist
                return apache.HTTP_NOT_FOUND

            if booking.state not in "if":
                # Booking has wrong state
                return apache.HTTP_NOT_FOUND
        
        m3u  = '#EXTM3U\n'
        m3u += '#EXTINF:0, %s (%s, %s)\n' % (title, booking.channel.name, startTimeS)
        m3u += '#EXTVLCOPT:vout-filter=deinterlace\n'
        m3u += '#EXTVLCOPT:deinterlace-mode=blend\n'

        if not browse:
            if booking.state == 'f':
                # Finished booking, stream on-demand, file-by-file

                # Count number of .mpg files
                numFiles = len(glob.glob("%s*.mpg" % booking.GetBasePath(self.req.config)))
                webBasePath = booking.GetWebBasePath(self.req.config)

                m3u += '\n'.join(['http://%s.%s%s_%03i.mpg\n' % (self.req.config["network"]["host"], self.req.config["network"]["domain"], webBasePath, i) for i in xrange(0, numFiles)])
            else:
                # Booking in progress: Stream live
                tuner = andp.model.tuners.GetTuner(self.req.cursor, self.req.config, booking.tunerID)

                if isinstance(booking.channel, andp.model.tuners.Channel):
                    m3u += 'rtp://@%s:1234\n' % (tuner.mcGroup)
                else:
                    m3u += booking.channel.id
        else:
            m3u += andp.model.tuners.GetChannelURIByName(self.req.cursor, name)
        
        self.SendHeader(contentType = "application/x-mpegurl")
        #self.SendHeader(contentType = "text/plain")
        self.Write(m3u)
        return apache.OK

class LibraryErrInfo(Page):
    path = "/library/errinfo"

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)
        bookingID = form["bID"].value

        booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

        html = self.LoadTemplate()

        d = {}
        if booking.title:
            d["title"]   = EH(booking.title)
        else:
            d["title"]   = '<em>Untitled</em>'

        d["channelName"] = EH(booking.channel.name)
        d["startTime"]   = booking.startTime.strftime("%d %B %Y")

        d["error"] = EH(booking.notice)

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class LibraryWatch(Page):
    """

    Note: This class is subclassed by bookings.BookingsWatch
    
    """
    
    path = "/library/watch"

    def GetDownloadHTML(self, booking):
        numMPGFiles = len(glob.glob("%s*.mpg" % booking.GetBasePath(self.req.config)))
        webBasePath = booking.GetWebBasePath(self.req.config)
       
        oggURL = "http://%s.%s%s.ogg" % (self.req.config["network"]["host"], self.req.config["network"]["domain"], webBasePath)
        mpgLinks = ", ".join(['<a href="http://%s.%s%s_%03i.mpg">part %i</a>' % (self.req.config["network"]["host"], self.req.config["network"]["domain"], webBasePath, i, i + 1) for i in xrange(numMPGFiles)])

        html  = '<p><strong>Download:</strong>&nbsp;&nbsp;&nbsp; MPEG-2 format (%s)&nbsp;&nbsp;&nbsp; ' % (mpgLinks,)
        
        if os.path.exists(booking.GetBasePath(self.req.config) + ".ogg"):
            html += '<a href="%s">Ogg Theora format</a>' % (oggURL,)
        else:
            html += 'Ogg Theora version not ready yet, try again in a few minutes'

        html += '</p>\n'
        
        return html

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)
        bookingID = form["bID"].value

        booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

        html = self.LoadTemplate()

        d = {}
        
        if booking.title:
            d["title"]   = EH(booking.title)
        else:
            d["title"]   = '<em>Untitled</em>'

        d["channelName"] = EH(booking.channel.name)
        d["startTime"]   = booking.startTime.strftime("%d %B %Y")

        d["preview"]  = self.GetPreviewHTML(booking)
        d["details"]  = self.GetDetailsHTML(booking)

        d["download"] = self.GetDownloadHTML(booking)

        d["vlcURL"] = '/vlc/%s.vlc' % booking.id

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class Library(Page):
    """

    Library page and subpages

    """

    path = "/library/" #"/library/*"

    def GetFailedHTML(self):
        failed = andp.model.bookings.GetBookings(self.req.cursor, 'e')
        failed.reverse()

        if failed:
            html  = '<h2>Failed bookings</h2>\n'
            html += self.BookingsToHTML(failed)
            return html
        else:
            return ""

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        #path = self.req.uri[8:]

        form = mod_python.util.FieldStorage(self.req)

        if form.has_key("sort") and form.has_key("sortDir"):
            orderBy = form["sort"]
            sortDir = form["sortDir"]
            if orderBy not in ["title", "channelID", "startTime", "record", "username"]:
                orderBy = "startTime"
            if sortDir not in ["asc", "desc"]:
                sortDir = "desc"
        else:
            orderBy = "startTime"
            sortDir= "desc"

        if form.has_key("sortColumn"):
            sortColumn = form["sortColumn"]
        else:
            sortColumn = "date"

        bookings = [b for b in andp.model.bookings.GetBookings(self.req.cursor, 'f', orderBy, sortDir) if b.record]
        # bookings.reverse() # We need list to be in reverse chronological order

        d = {}
        d["library"] = self.BookingsToHTML(bookings, sortColumn, sortDir)
        d["failed"]  = self.GetFailedHTML()

        html = self.LoadTemplate("main.html")

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class Library2(Page):
    """

    New style library page and subpages

    """

    path = "/library2/" #"/library/*"

    # pathParts = re.compile(r'/library2/(\d\d\d\d/)(\d\d/)(\d\d/)(.*)')

    def GetBrowseParams(self):
        params = self.req.uri[1:].split("/")
        retDict = {}
        numParams = 0
        if len(params) > 1 and params[1] != "":
            retDict["year"] = params[1]
            numParams += 1
        else:
            retDict["year"] = None

        if len(params) > 2 and params[2] != "":
            retDict["month"] = params[2]
            numParams += 1
        else:
            retDict["month"] = None

        if len(params) > 3 and params[3] != "":
            retDict["day"] = params[3]
            numParams += 1
        else:
            retDict["day"] = None

        if len(params) > 4 and params[4] != "":
            retDict["channel"] = params[4]
            numParams += 1
        else:
            retDict["channel"] = None

        return retDict, numParams

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        params, numParams = self.GetBrowseParams()

        form = mod_python.util.FieldStorage(self.req)

        if form.has_key("sort") and form.has_key("sortDir"):
            orderBy = form["sort"]
            sortDir = form["sortDir"]
            if orderBy not in ["title", "channelID", "startTime", "record", "username"]:
                orderBy = "startTime"
            if sortDir not in ["asc", "desc"]:
                sortDir = "desc"
        else:
            orderBy = "startTime"
            sortDir= "desc"

        channels = andp.model.bookings.GetRecordedChannels(self.req.cursor)
        years = andp.model.bookings.GetYearsWithRecordings(self.req.cursor)
        if params["year"] == None:
            narrowBy = "all"
            bookings = []
        elif params["year"] != None and params["month"] == None:
            # Soek paa aar
            pass
        elif params["month"] != None and params["day"] == None:
            # Soek paa aar og maaned
            pass
        elif params["day"] != None and params["channel"] == None:
            # Soek paa aar, maaned og dag
            pass

        d = {}
        d["library"] = self.BrowseBookingsToHTML(numParams, params, sortDir)
        d["failed"] = ""
        d["numSimChannels"] = 2
        html = self.LoadTemplate("main.html")

        self.SendHeader()
        self.Write(html % d)
        return apache.OK
