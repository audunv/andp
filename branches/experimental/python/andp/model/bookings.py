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

"""

This module defines classes, functions and database tables
representing bookings

"""

import urllib, datetime, os, shutil

import andp.exceptions

from andp.db import PsE

import andp.model.tuners

# Define constants
DAY = "1 DAY"
MONTH = "1 MONTH"
YEAR = "1 YEAR"


class Booking(object):
    def __init__(self, username, bookingID, startTime, endTime, channel, tunerID, record, title, description, state = None, notice = None):
        """

        Booking object

          username:    Username of owner
          bookingID:   Booking ID (None for new bookings)
          startTime:   Start date and time (tuple or datetime)
          endTime:     See above
          channel:     Channel to broadcast/record from
          tunerID:     Tuner ID (None to allocate automatically; ignored for IP channels)
          record:      True if programme should be recorded as well as broadcast
          title:       User's booking title
          description: User's description of booking

        Optional parameters:

          state:       State of recording (see tables.sql)
          notice:      Status message or similar
        
        """

        #if type(startTime) == tuple:
        #    year, month, day, hour, mint, sec = startTime
        #    startTime = datetime.datetime(year, month, day, hour, mint, sec)
        
        #if type(endTime) == tuple:
        #    year, month, day, hour, mint, sec = endTime
        #    endTime = datetime.datetime(year, month, day, hour, mint, sec)

        assert isinstance(channel, andp.model.tuners.BaseChannel)
        
        self.username    = username
        self.id          = bookingID
        self.startTime   = startTime
        self.endTime     = endTime
        self.channel     = channel
        self.tunerID     = tunerID
        self.record      = record
        self.title       = title
        self.description = description
        self.state       = state
        self.notice      = notice

    def Save(self, cursor, username):
        """

        Create or update booking

          username: username of current user (for authentication)

        Returns booking ID
        
        """

        # Only proceed if booking is new or it belongs to the authenticated user
        PsE(cursor, "select username from bookings where id=%s", (self.id,))
        assert (not self.id) or (cursor.fetchone()[0] == username)

        # Only proceed if booking is new or it is in "wait" state
        PsE(cursor, "select state from bookings where id=%s", (self.id,))
        if self.id and cursor.fetchone()[0] != 'w':
            raise andp.exceptions.NoLongerEditable

        if isinstance(self.channel, andp.model.tuners.Channel):
            # Always reallocate tuner for satellite channels
            self.tunerID = andp.model.tuners.GetAvailableTuners(cursor, self.channel.id, self.startTime, self.endTime, self.id)[0]
            if not self.tunerID:
                raise andp.exceptions.NoTunersAvailable
        else:
            self.tunerID = None

        if not self.id:
            self.id = andp.model.RandomHexString(32)
            bookingIsNew = True
        else:
            bookingIsNew = False

        if isinstance(self.channel, andp.model.tuners.Channel):        
            if bookingIsNew:
                PsE(cursor, "insert into bookings (id, username, startTime, endTime, channelID, tunerID, record, title, description) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (self.id, self.username, self.startTime, self.endTime, self.channel.id, self.tunerID, self.record, self.title, self.description))
            else:
                PsE(cursor, "update bookings set startTime=%s, endTime=%s, channelID=%s, tunerID=%s, record=%s, title=%s, description=%s where id=%s", (self.startTime, self.endTime, self.channel.id, self.tunerID, self.record, self.title, self.description, self.id))
        else:
            if bookingIsNew:
                PsE(cursor, "insert into bookings (id, username, startTime, endTime, ipURI, record, title, description) values (%s, %s, %s, %s, %s, %s, %s, %s)", (self.id, self.username, self.startTime, self.endTime, self.channel.id, self.record, self.title, self.description))
            else:
                PsE(cursor, "update bookings set startTime=%s, endTime=%s, ipURI=%s, record=%s, title=%s, description=%s where id=%s", (self.startTime, self.endTime, self.channel.id, self.record, self.title, self.description, self.id))

        return self.id

    def GetWebBasePath(self, cfg):
        """

        Returns booking's (potential) path as seen by web clients (excluding file extension)
        
        """

        year, month, day, hour, mint, sec = self.startTime.timetuple()[:6]

        # To make the path prettier, we only use the first four digits
        # of the bookingID
        return "/video/" + "/".join(("%04i" % year, "%02i" % month, "%02i" % day, self.id, "%04i%02i%02i_%02i%02i%02i_%s" % (year, month, day, hour, mint, sec, self.id[:4])))

    def GetBasePath(self, cfg):
        """

        Returns booking's (potential) file system path (excluding file extension)
        
        """

        year, month, day, hour, mint, sec = self.startTime.timetuple()[:6]

        # To make the path prettier, we only use the first four digits
        # of the bookingID
        return os.path.join(cfg["path"]["library"], "%04i" % year, "%02i" % month, "%02i" % day, self.id, "%04i%02i%02i_%02i%02i%02i_%s" % (year, month, day, hour, mint, sec, self.id[:4]))

    def Delete(self, cursor, cfg, username):
        """

        Delete booking

          username: username of current user (for authentication)
        
        """

        # Only proceed if booking belongs to the authenticated user
        assert self.username == username

        # Only proceed if booking is in wait or finished state
        if self.state not in 'wf':
            raise andp.exceptions.NotDeletable

        # Delete recordings from disk
        if self.state in 'f':
            dirPath = os.path.split(self.GetBasePath(cfg))[0]
            shutil.rmtree(dirPath)

        PsE(cursor, "delete from bookings where id=%s", (self.id,))

    def SetState(self, cursor, newState, notice = None):
        """

        Update booking's state

          newState: e, f, i or w
          notice:   Notice to user (optional)
        
        """

        if notice:
            PsE(cursor, "update Bookings set state=%s, notice=%s where id=%s", (newState, notice[:16384], self.id))
        else:
            PsE(cursor, "update Bookings set state=%s where id=%s", (newState, self.id))

    def SetRealDuration(self, cursor, duration):
        """

        Set recording's real duration (since booked start time and
        actual start time are not always the same).

          duration: Actual duration in seconds
        
        """

        # For some reason, the line below doesn't work...
        #PsE(cursor, "update Bookings set realDuration=%f where id=%s", (duration, self.id))

        # ...so we have to do it like this instead:
        PsE(cursor, "update Bookings set realDuration=%f where id=%%s" % duration, (self.id,))

    def GetRealDuration(self, cursor):
        """

        Get recording's real duration (since booked start time and
        actual start time are not always the same).
        
        """

        PsE(cursor, "select realDuration from Bookings where id=%s", (self.id,))
        return cursor.fetchone()[0]

def GetRecordedChannels(cursor):

    channelDict = dict([(c.id, c) for c in andp.model.tuners.GetChannels(cursor)])

    PsE(cursor, "select channelID from bookings where record group by channelID")
    
    channels = []

    for channelID in cursor.fetchall():
        channels.append(channelDict[channelID[0]])
    
    return channels

def GetYearsWithRecordings(cursor):
    PsE(cursor, "select to_char(endtime, 'YYYY') from bookings where record group by to_char(endtime, 'YYYY')")
    return cursor.fetchall()

def GetMonthsWithRecordings(cursor, year):
    PsE(cursor, "select to_char(endtime, 'MM') from bookings where record and (startTime, endTime) overlaps (DATE '%s-01-01', DATE '%s-12-31') group by to_char(endtime, 'MM') order by to_char(endtime, 'MM') asc" % (year, year))
    return cursor.fetchall()

def GetDaysWithRecordings(cursor, year, month):
    PsE(cursor, "select to_char(endtime, 'DD') from bookings where record and (startTime, endTime) overlaps (DATE '%s-%s-01', INTERVAL '1 month') group by to_char(endtime, 'DD') order by to_char(endtime, 'DD') asc" % (year, month))
    return cursor.fetchall()

def GetBookingsByInterval(cursor, narrowBy, interval, orderBy = "startTime", orderDir = "desc"):

    channels = dict([(c.id, c) for c in andp.model.tuners.GetChannels(cursor)])
    #reverseChannels = dict([(c, c.id) for c in andp.model.tuners.GetChannels(cursor)])

    where = " where (startTime, endTime) overlaps (DATE '%s', INTERVAL '%s')" % (narrowBy, interval)

    bookings = []

    PsE(cursor, "select id, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username from Bookings%s order by %s %s" % (where, orderBy, orderDir))

    for bookingID, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username in cursor.fetchall():
        if channelID:
            channel = channels[channelID]
        else:
            channel = channels[ipURI]

        booking = Booking(username, bookingID, startTime, endTime, channel, tunerID, record, title, description, state, notice)

        bookings.append(booking)

    return bookings

def GetBookings(cursor, states = '', orderBy = "startTime", orderDir = "asc"):
    """

    Returns list of Booking objects sorted by start time as default

      states:      Filter by booking state (e, f, i and/or w).
                   Default: All states.
    
    """

    if states:
        where = " where " + " or ".join(["state='%s'" % c for c in states])
    else:
        where = ""

    channels = dict([(c.id, c) for c in andp.model.tuners.GetChannels(cursor)])

    bookings = []

    PsE(cursor, "select id, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username from Bookings%s order by %s %s" % (where, orderBy, orderDir))

    for bookingID, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username in cursor.fetchall():
        if channelID:
            channel = channels[channelID]
        else:
            channel = channels[ipURI]

        booking = Booking(username, bookingID, startTime, endTime, channel, tunerID, record, title, description, state, notice)

        bookings.append(booking)

    return bookings

def GetBooking(cursor, bookingID):
    """

    Returns Booking object bookingID, or None it couldn't be found
    
    """

    channels = dict([(c.id, c) for c in andp.model.tuners.GetChannels(cursor)])

    PsE(cursor, "select id, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username from Bookings where id=%s", (bookingID,))

    try:
        bookingID, startTime, endTime, channelID, tunerID, ipURI, record, state, notice, title, description, username = cursor.fetchone()
    except TypeError:
        # Not found
        return None
    else:
        if channelID:
            channel = channels[channelID]
        else:
            channel = channels[ipURI]

        booking = Booking(username, bookingID, startTime, endTime, channel, tunerID, record, title, description, state, notice)
        
        return booking
