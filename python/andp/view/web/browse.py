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

import pprint, os, stat, re, glob, xmltv, datetime, pytz

import mod_python.util

from mod_python import apache

import andp.model.bookings

import andp.view.web
import andp.view.web.widgets
import andp.model.bookings

from andp.view.web import Page, Dispatcher, ConfirmationDialog, EH

class Browse(Page):
    """

    Library page and subpages

    """

    path = "/browse/" #"/library/*"


    def Main(self):
        self.xmlfilename = "/tmp/xmltv.xml"
        self.timezone = "Europe/Oslo"
        self.timezonehandler = pytz.timezone(self.timezone)
        self.timeformatnownext = "%H:%M:%S"
        self.timeformat = "%d-%m-%Y %H:%M:%S"
        
        d = {}
        fakeBooking = andp.model.bookings.FakeBooking()
        form = mod_python.util.FieldStorage(self.req)
        channels = [(c.id, "%s (%s)" % (c.name, c.provider)) for c in andp.model.tuners.GetChannels(self.req.cursor, 'e', 'i')]

        if form.has_key("channel"):
            fakeBooking.id = andp.model.tuners.GetChannelByID(self.req.cursor, form["channel"].value).name.replace(" ", "%20")
        else:
            trash, fakeBooking.id = channels[0]
            fakeBooking.id = fakeBooking.id.replace(" (IPTV)", "").replace(" ", "%20")
            
        d["channel"] = fakeBooking.id.replace("%20", " ")
        d["curProgramme"] = self.GetCurrentProgramme(self.GetChannelListings(fakeBooking.id))
        d["view"] = self.GetPreviewHTML(fakeBooking)
        d["channels"] = andp.view.web.widgets.SelectWidget(self, "channel", options = channels).GetHTML().replace("<select", '<select onchange="this.form.submit()"')
        d["today"] = self.CreateNowNextTable(self.GetChannelListings(fakeBooking.id))
        html = self.LoadTemplate("main.html")

        html = html.replace("</head>", '<script type="text/javascript" src="/javascript/browse.js"></script>\n</head>').replace("<body>", '<body onload="remButton();">')

        self.SendHeader()
        self.Write(html % d)
        return apache.OK

    def GetChannelNameToIDMapping(self):
        channels = xmltv.read_channels(open(self.xmlfilename))
        channelsdict = {}
        for item in channels:
            name, trash = item["display-name"][0]
            channelsdict[name] = item["id"]
        return channelsdict

    def CompareProgrammeListings(self, fieldname):
        def compare_two_dicts(a, b):
            return cmp(a[fieldname], b[fieldname])
        return compare_two_dicts

    def GetCurrentProgramme(self, listings):
        listings.sort(self.CompareProgrammeListings("start"))
        today = []

        for item in listings:
            if datetime.datetime.strptime(item["start"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today() and datetime.datetime.strptime(item["stop"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today():
                    continue
            else:
                today.append(item)

        return today[0]["title"][0][0].encode("utf-8")

    def CreateNowNextTable(self, listings):
        outp = "<table><th></th><th>Start</th><th>Title</th><th>Description</th>\n"
        listings.sort(self.CompareProgrammeListings("start"))
        today = []
        for item in listings:
            if datetime.datetime.strptime(item["start"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today() and datetime.datetime.strptime(item["stop"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today():
                    continue
            else:
                today.append(item)

        today.sort(self.CompareProgrammeListings("start"))
        now = today[0]
        now["time"] = "Current programme"
        next = today[1]
        next["time"] = "Next programme"

        for item in [now, next]:
            try:
                desc = item["desc"][0][0]
            except KeyError:
                desc = ""

            bookLink = ""
            
            outp += u"""<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n""" % (item["time"], self.timezonehandler.localize(self.ConvertXMLTVTimeToUTC(item["start"])).strftime(self.timeformatnownext), item["title"][0][0], desc)

        outp += "</table>"

        return outp     

    def ConvertXMLTVTimeToUTC(self, xmltv):
        utctime = datetime.datetime.strptime(xmltv[:-6], "%Y%m%d%H%M%S")
        hours = int(xmltv[-4:-2])
        minutes = int(xmltv[-2:]) * 60
        if xmltv[-5] == "-":
            utctime = utctime + datetime.timedelta(hours, minutes)
        else:
            utctime = utctime - datetime.timedelta(hours, minutes)

        return utctime

    def CreateProgrammeTable(self, listings, justToday = False, noDesc = False):
        outp = "<table><th>Start</th><th>Stop</th><th>Title</th><th>Description</th>\n"
        listings.sort(self.CompareProgrammeListings("start"))
        for item in listings:
            try:
                desc = item["desc"][0][0]
            except KeyError:
                desc = ""


            if datetime.datetime.strptime(item["start"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today() and datetime.datetime.strptime(item["stop"][:-6], "%Y%m%d%H%M%S") < datetime.datetime.today():
                continue

            if justToday:
                if datetime.datetime.strptime(item["stop"][:-6], "%Y%m%d%H%M%S") > datetime.datetime.today() + datetime.timedelta(1):
                    continue
                
            outp += u"<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n" % (self.timezonehandler.localize(self.ConvertXMLTVTimeToUTC(item["start"])).strftime(self.timeformat), self.timezonehandler.localize(self.ConvertXMLTVTimeToUTC(item["stop"])).strftime(self.timeformat), item["title"][0][0], desc)

        outp += "</table>"

        return outp
        
    def GetChannelListings(self, channelname):
        channelname = channelname.replace("%20", " ")
        xmltv.locale = "UTF-8"
        channels = self.GetChannelNameToIDMapping()
        programmes = xmltv.read_programmes(open(self.xmlfilename))
        listings = []
        for item in programmes:
            if item["channel"] == channels[channelname]:
                listings.append(item)
        return listings
