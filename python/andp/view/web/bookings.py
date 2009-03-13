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

This module renders the front page and other top-level pages

"""

import time, datetime, subprocess, os

import mod_python.util

from mod_python import apache

import andp.model.bookings

import andp.view.web
import andp.view.web.widgets
import andp.view.web.library

from andp.view.web import Page, Dispatcher, ConfirmationDialog, EH

class BookingsDispatch(Dispatcher):
    path = "/dispatch"

    argumentName = "bID"
    actions      = ["watch", "edit", "delete"]

    default = "edit"

#class M3U(Page):
#    path = "/m3u"
#
#    showDebug = False
#
#    def Main(self):
#        #if self.user == None:
#        #    self.RedirectToLogin()
#        #    return
#
#        form = mod_python.util.FieldStorage(self.req)
#        url = form["url"].value
#
#        assert url.startswith("udp://@")
#
#        self.req.headers_out["Connection"] = "close"
#        self.SendHeader("audio/x-mpegurl")
#        self.Write(url + "\n")
#
#        return apache.OK
    
class Bookings(Page):
    """

    Bookings page
    
    """

    path = "/"

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        nowPlaying = andp.model.bookings.GetBookings(self.req.cursor, 'i')
        scheduled  = andp.model.bookings.GetBookings(self.req.cursor, 'w')

        d = {}

        if nowPlaying:
            d["nowPlaying"] = self.BookingsToHTML(nowPlaying)
        else:
            d["nowPlaying"] = '<p>No broadcasts or recordings are currently in progress.</p>'
        
        if scheduled:
            d["scheduled"] = self.BookingsToHTML(scheduled)
        else:
            d["scheduled"] = '<p>There are no scheduled broadcasts or recordings.</p>'

        numTuners = len(self.req.config["tuners"]["hosts"])
        if numTuners == 1:
            d["numSimChannels"] = "1 channel"
        else:
            d["numSimChannels"] = "%i channels" % numTuners
        
        html = self.LoadTemplate("main.html")

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class BookingsDelete(ConfirmationDialog):
    """

    /delete
    
    """

    path = "/delete"

    def SetVariables(self):
        self.title      = "Delete booking?"
        self.message    = '<p>Are you sure you want to permanently delete this booking?</p>'
        self.hiddenName = "bID"
        
        self.labelYes = "Delete booking"
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

# We'll do it this way to get exactly the same functionality, but
# displayed in the correct tab
class BookingsWatch(Page):
    path = "/watch"

    def GetRealTimeHTML(self, booking):
        tuner = andp.model.tuners.GetTuner(self.req.cursor, self.req.config, booking.tunerID)
#        url = 'rtp://%s.%s@%s' % (self.req.config["network"]["host"], self.req.config["network"]["domain"], tuner.mcGroup)
        url = 'rtp://@%s:1234' % (tuner.mcGroup)

        return '<p><strong>Direct URL:</strong>&nbsp;&nbsp;&nbsp; %s &nbsp;&nbsp;&nbsp;(copy and paste into VLC)</p>' % url

    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)
        bookingID = form["bID"].value

        booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

        if booking.state == "f":
            # If broadcast/recording has finished in the meantime, we'll redirect to /library/watch?...
            self.Redirect("/library/watch?bID=" + bookingID)
            return
        elif booking.state != "i":
            # This means an error occured while user was twiddling
            # his/her thumbs. We'll redirect to /library/errinfo?...
            self.Redirect("/library/errinfo?bID=" + bookingID)
            return

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

        d["realTime"] = self.GetRealTimeHTML(booking)

        d["vlcURL"] = '/vlc/%s.vlc' % booking.id

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

class BookingsEdit(Page):
    """

    Bookings page
    
    """

    path = "/edit"

    def BuildBooking(self, widgets, form):
        """

        Builds a booking object based on list of widgets data in form

        """
        
        sYear, sMonth, sDay = widgets["startDate"].ParseInput(form)[1]
        sHour, sMin, sSec   = widgets["startTime"].ParseInput(form)[1]

        eYear, eMonth, eDay = widgets["endDate"].ParseInput(form)[1]
        eHour, eMin, eSec   = widgets["endTime"].ParseInput(form)[1]

        startTime = datetime.datetime(sYear, sMonth, sDay, sHour, sMin, sSec)
        endTime   = datetime.datetime(eYear, eMonth, eDay, eHour, eMin, eSec)

        channelID = widgets["channel"].ParseInput(form)[1]

        record = (widgets["bType"].ParseInput(form)[1] == 'br')

        title = widgets["title"].ParseInput(form)[1]
        description = widgets["description"].ParseInput(form)[1]
        
        try:
            bookingID = form["bID"].value
        except KeyError:
            bookingID = None

        if bookingID:
            booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

            booking.startTime   = startTime
            booking.endTime     = endTime
            booking.channelID   = channelID
            booking.record      = record
            booking.title       = title
            booking.description = description
        else:
            booking = andp.model.bookings.Booking(self.user.username, None, startTime, endTime, channelID, None, record, title, description)

        return booking
    
    def GetNewWidgets(self):
        """

        Returns dictionary of widgets to be used for defining new booking
        
        """

        channels = [(c.id, "%s (%s)" % (c.name, c.provider)) for c in andp.model.tuners.GetChannels(self.req.cursor, 'e')]
        
        widgets = {}

        endDT = time.localtime(time.time() + 3600) # One hour in the future

        widgets["startTime"]   = andp.view.web.widgets.TimeWidget(self, "startTime")
        widgets["startDate"]   = andp.view.web.widgets.DateWidget(self, "startDate")
        
        widgets["endTime"]     = andp.view.web.widgets.TimeWidget(self, "endTime", value = endDT[3:5])
        widgets["endDate"]     = andp.view.web.widgets.DateWidget(self, "endDate", value = endDT[:3])

        widgets["channel"]     = andp.view.web.widgets.SelectWidget(self, "channel", options = channels)
        widgets["bType"]      = andp.view.web.widgets.RadioWidget(self, "bType", options = (("br", "Broadcast and record"), ("b", "Broadcast only")))
        widgets["title"]       = andp.view.web.widgets.TextWidget(self, "title", cols = 40)
        widgets["description"] = andp.view.web.widgets.TextWidget(self, "description", cols = 40, rows = 10)

        return widgets

    def GetEditWidgets(self, booking):
        """

        Returns dictionary of widgets to be used for editing existing booking
        
        """

        channels = [(c.id, "%s (%s)" % (c.name, c.provider)) for c in andp.model.tuners.GetChannels(self.req.cursor, 'e')]

        sTuple = booking.startTime.timetuple()
        eTuple = booking.endTime.timetuple()

        if booking.record:
            bType = 'br'
        else:
            bType = 'r'
        
        widgets = {}

        widgets["startTime"]   = andp.view.web.widgets.TimeWidget(self, "startTime", value = sTuple[3:5])
        widgets["startDate"]   = andp.view.web.widgets.DateWidget(self, "startDate", value = sTuple[:3])
        
        widgets["endTime"]     = andp.view.web.widgets.TimeWidget(self, "endTime", value = eTuple[3:5])
        widgets["endDate"]     = andp.view.web.widgets.DateWidget(self, "endDate", value = eTuple[:3])

        widgets["channel"]     = andp.view.web.widgets.SelectWidget(self, "channel", options = channels, value = booking.channelID)
        widgets["bType"]       = andp.view.web.widgets.RadioWidget(self, "bType", options = (("b", "Broadcast only"), ("br", "Broadcast and record")), value = bType)
        widgets["title"]       = andp.view.web.widgets.TextWidget(self, "title", cols = 40, value = booking.title)
        widgets["description"] = andp.view.web.widgets.TextWidget(self, "description", cols = 40, rows = 10, value = booking.title)

        return widgets

    def HandleEdit(self, bookingID, form = None, errMsgs = {}):
        if bookingID:
            booking = andp.model.bookings.GetBooking(self.req.cursor, bookingID)

            widgets = self.GetEditWidgets(booking)
            title   = 'Edit booking'
        else:
            widgets = self.GetNewWidgets()
            title   = 'New booking'

        d = dict([(name, obj.GetHTML(form)) for name, obj in widgets.items()])
        d["bID"]   = bookingID
        d["pageTitle"] = title

        if form:
            d.update(dict([(name + "_errmsg", w.ParseInput(form)[2]) for name, w in widgets.items()]))
        else:
            d.update(dict([(name + "_errmsg", "") for name in widgets.keys()]))

        d.update(errMsgs)

        self.SendHeader()
        self.Write(self.LoadTemplate() % d)

        return apache.OK
    
    def Main(self):
        if self.user == None:
            self.RedirectToLogin()
            return

        form = mod_python.util.FieldStorage(self.req)

        try:
            bookingID = form["bID"].value
        except:
            bookingID = ""

        if form.has_key("book"):
            widgets = self.GetNewWidgets()

            if not self.ValidateInput(widgets, form):
                return self.HandleEdit(bookingID, form)

            try:
                booking = self.BuildBooking(widgets, form)
            except andp.exceptions.InvalidTime:
                return self.HandleEdit(bookingID, form, {"startTime_errmsg": 'Invalid start or end time'})
            except andp.exceptions.InvalidDuration:
                return self.HandleEdit(bookingID, form, {"startTime_errmsg": 'Booking is too long'})

            # This is probably not the right place to check for these things
            if booking.endTime < datetime.datetime.now(booking.endTime.tzinfo):
                return self.HandleEdit(bookingID, form, {"endTime_errmsg": 'End time must be in the future'})
            elif booking.endTime - booking.startTime >= datetime.timedelta(0, 3600 * 12):
                return self.HandleEdit(bookingID, form, {"startTime_errmsg": "Recordings must last less than 12 hours"})
            elif booking.endTime <= booking.startTime:
                return self.HandleEdit(bookingID, form, {"endTime_errmsg": "End time must be later than start time"})

            try:
                booking.Save(self.req.cursor, self.user.username)
            except andp.exceptions.NoTunersAvailable:
                return self.HandleEdit(bookingID, form, {"channel_errmsg": 'No tuners are available for this channel and time interval'})
            except andp.exceptions.NoLongerEditable:
                return self.WriteMessage("No longer editable", "This booking is no longer editable", "./")

            #raise "%s %s %s" % (booking.startTime, datetime.datetime.now(), booking.startTime <= datetime.datetime.now())

            if booking.startTime <= datetime.datetime.now():
                # If startTime has passed, start recording immediately

                # We must commit now, before broadcast.py tries to
                # read from the database
                self.req.conn.commit()
                
                scriptPath = os.path.join(self.req.config["path"]["scripts"], "broadcast.py")
                cfgPath    = self.req.get_options()["andpConfigPath"]

                cmd = "%s %s %s &" % (scriptPath, cfgPath, booking.id)
                proc = subprocess.Popen(cmd, shell = True)

                # Wait a bit so that recording process has time to update booking state
                time.sleep(4)

                #raise str(proc.poll())

            self.Redirect("./")

        elif form.has_key("cancel"):
            self.Redirect("./")

        else:
            # Step 1: Edit or new
            return self.HandleEdit(bookingID)
