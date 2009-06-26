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
representing tuners and channels.

"""

import urllib, urllib2, zlib, time, md5, re

import andp.exceptions

from andp.db import PsE

# Screenshots with an entropy smaller than this will be assumed to
# indicate decryption problems
ENTROPY_LIMIT = 0.002
MINIMUM_SIZE  = 8000

URI = re.compile(r'^[a-z]{2,}://')

class Tuner(object):
    def __init__(self, host, password, mcGroup):
        self.host = host
        self.password = password
        self.mcGroup = mcGroup

    def GetTSURL(self):
        """

        Returns URL of TS stream. Should be called after
        SwitchToChannel.
        
        """

        authHandler = urllib2.HTTPBasicAuthHandler()
        authHandler.add_password('dreambox', self.host, "root", self.password)
        opener = urllib2.build_opener(authHandler)
        urllib2.install_opener(opener)

        tsURL  = urllib2.urlopen("http://%s/video.m3u" % self.host).read()

        return tsURL
        
    def SwitchToChannel(self, channelID):
        """

        Switches to channel channelID. Does its best to catch
        exceptions in an ordely manner, but Dreamboxes are not always
        straightforward to interpret.
        
        """
        
        authHandler = urllib2.HTTPBasicAuthHandler()
        authHandler.add_password('dreambox', self.host, "root", self.password)
        opener = urllib2.build_opener(authHandler)
        urllib2.install_opener(opener)
    
        url = "http://%s/cgi-bin/zapTo?mode=zap&path=%s" % (self.host, channelID)

        try:
            f = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            # /zapTo always yields HTTP code 204 and an empty document
            # (whether successful or not). urllib2 will therefore always
            # raise an exception :-(
            pass

        # It seems that we need to sleep a bit to let the tuning take
        # effect
        time.sleep(1)

        # Since we don't know if zapTo was successful we need to check if
        # tuner is actually tuned to a channel.

        # If channel name is "-1", DreamBox probably received invalid
        # parameters
        channelName = urllib2.urlopen("http://%s/channels/getcurrent" % self.host).read() 
        if channelName == "-1":
            raise andp.exceptions.TuningError, "Unable to tune to channel. Check parameters and signal."

        # Even if channel is properly tuned Dreambox may not be able to
        # decrypt it.  Since we'll receive data even if it's scrambled we
        # need to check for an image.  If image is uniformly black (and
        # thus very compressible) we'll assume decryption problems and
        # raise an exception.
        time.sleep(5)
        for i in xrange(0, 10): # Try up to ten times (sleeping 1 second between attempts)
            urllib2.urlopen("http://%s/body?mode=controlScreenShot" % self.host).read()
            bmp = urllib2.urlopen("http://%s/root/tmp/screenshot.jpg" % self.host).read()

            #entropy = float(len(zlib.compress(bmp))) / len(bmp)

            #print entropy

            #if entropy >= ENTROPY_LIMIT:
            #    break

            open("/tmp/cam.txt", "a").write("Len of screenshot: %s" % len(bmp))
            open("/tmp/screen.jpg", "w").write(bmp)

            if len(bmp) > MINIMUM_SIZE:
                break
            
            time.sleep(1)
            
        # Entropy of a blank image seems to be around 0.001
        #        if entropy < ENTROPY_LIMIT:
        if len(bmp) < MINIMUM_SIZE:
            raise andp.exceptions.TuningError, "Unable to decrypt channel. Check CAM and subscription."

class BaseChannel(object):
    "Base class for all channels. Name is due to historical reasons"
    def __init__(self, cID, name):
        self.id = cID
        self.name = name

    def __cmp__(self, other):
        if self.name < other.name:
            return -1
        elif self.name > other.name:
            return 1
        elif self.provider < other.provider:
            return -1
        elif self.provider > other.provider:
            return 1
        else:
            return 0

class Channel(BaseChannel):
    "Dreambox-based channels"
    def __init__(self, cID, name, provider, enabled):
        BaseChannel.__init__(self, cID, name)
        
        self.provider = provider
        self.enabled  = enabled

class IPChannel(BaseChannel):
    "Streamed channels (from any URI understood by VLC)"
    def __init__(self, uri, name):
        BaseChannel.__init__(self, uri, name)
        self.provider = "IPTV"

def GetTuner(cursor, cfg, tunerID):
    """

    For completeness and consistency: Returns a Tuner object based on
    tunerID, or None if tunerID couldn't be found. Does NOT look in
    the database.
    
    """

    try:
        password, mcGroup = [r[1:3] for r in cfg["tuners"]["hosts"] if r[0] == tunerID][0]
    except IndexError:
        # Not found
        return None

    tuner = Tuner(tunerID, password, mcGroup)

    return tuner

def UpdateChannelLists(cursor, hostsAndPasswords):
    """
    
    Updates host list and channel lists in database.

      hostAndPasswords: List of (hostname, password) tuples
    
    """

    # Delete old associations
    PsE(cursor, "delete from TunerChannels")

    # Remove tuner assocations for bookings that are finished
    PsE(cursor, "update bookings set tunerID=null where state='e' or state='f';")

    # Get old and new tuner IDs
    PsE(cursor, "select id from tuners")
    oldHosts = [r[0] for r in cursor.fetchall()]
    newHosts = [r[0] for r in hostsAndPasswords]

    # Delete tuners that are no longer in config file
    for oldHost in oldHosts:
        if oldHost not in newHosts:
            PsE(cursor, "delete from Tuners where id=%s", (oldHost,));

    # Add new tuners
    for newHost in newHosts:
        if newHost not in oldHosts:
            PsE(cursor, "insert into Tuners (id) values ('%s')" % (newHost,))

    # Cache known IDs, instead of asking database every time. We use a
    # dict since it's faster than a list for checking presence.
    PsE(cursor, "select id from channels")
    existingIDs = dict([(r[0], True) for r in cursor.fetchall()])

    for host, password in hostsAndPasswords:
        url = 'http://root:%s@%s/cgi-bin/getServices?ref=1:15:fffffffe:12:ffffffff:0:0:0:0:0:' % (password, host)

        for line in urllib.urlopen(url).readlines():
            try:
                cID, name, provider, ignore = [unicode(s) for s in line.strip().split(";")]
            except ValueError:
                # Unpack list of wrong size, presumably because we don't
                # have a channel line. Ignore.
                continue

            name = name.strip()
            if not name:
                # Empty names or names that contain only whitespace are dropped
                continue

            # This would make sure names and providers are updated, but takes more time:
            # PsE(cursor, "update Channels set name=%s, provider=%s where id=%s", (name, provider, cID))
            if not existingIDs.has_key(cID):
                PsE(cursor, "insert into Channels (id, name, provider) values (%s, %s, %s)", (cID, name, provider))
                existingIDs[cID] = True
                
            PsE(cursor, "insert into TunerChannels (tunerID, channelID) values (%s, %s)", (host, cID))

def CountChannels(cursor):
    """

    Returns (total number of channels, sorted list of (host, numberOfChannelsOnTuner))
    
    """

    PsE(cursor, "select count(id) from Channels")
    numChannels = cursor.fetchone()[0]

    PsE(cursor, "select tunerID, count(channelID) from TunerChannels group by tunerID order by tunerID;")
    tuners = cursor.fetchall()

    return numChannels, tuners

def GetChannels(cursor, filter = 'a', type = 'a'):
    """

    Returns Channel list of all known channels, sorted by name

      filter:
        e:           Return enabled channels only
        d:           Return disabled channels only
        Default return all channels

      type:
        s:           Return only sat channels
        i:           Return only IPTV channels

    """

    assert filter in 'ade'
    assert type in 'asi'

    if type != "i":
        if filter == 'e':
            PsE(cursor, "select id, name, provider, enabled from channels where enabled order by name")
        elif filter == 'd':
            PsE(cursor, "select id, name, provider, enabled from channels where not enabled order by name")
        else:
            PsE(cursor, "select id, name, provider, enabled from channels order by name")
        
        satChannels = [Channel(cID, name, provider, bool(enabled)) for cID, name, provider, enabled in cursor.fetchall()]
    else:
        satChannels = []

    if type != "s":
        PsE(cursor, "select uri, name from ipchannels order by name")
        ipChannels = [IPChannel(uri, name) for uri, name in cursor.fetchall()]
    else:
        ipChannels = []
    
    return sorted(satChannels + ipChannels)

def EnableChannel(cursor, cID):
    PsE(cursor, "update channels set enabled='t' where id=%s", (cID,))

def DisableChannel(cursor, cID):
    PsE(cursor, "update channels set enabled='f' where id=%s", (cID,))

def AddIPTVChannel(cursor, name, address):
    PsE(cursor, "insert into ipchannels values (%s, %s)", (address, name))

def RemoveIPTVChannel(cursor, cID):
    PsE(cursor, "delete from ipchannels where uri = %s", (cID, ))

def GetAvailableTuners(cursor, channelID, startTime, endTime, bookingID = None):
    if bookingID == None:
        bookingID = 'non-existing'

    PsE(cursor, "select GetAvailableTuners(%s, %s, %s, %s)", (channelID, startTime, endTime, bookingID))
    return [r[0] for r in cursor.fetchall()]

def GetChannelByID(cursor, cID):
    "Returns channel object with id == cID"

    if URI.search(cID):
        PsE(cursor, "select name from ipchannels where uri=%s", (cID,))
        return IPChannel(cID, cursor.fetchone()[0])
    else:
        PsE(cursor, "select name from channels where id=%s", (cID,))
        return Channel(cID, cursor.fetchone()[0])

def GetChannelURIByName(cursor, name):
    "Returns IPTV channel uri for name == name"
    PsE(cursor, "select uri from ipchannels where name=%s", (name, ))
    return cursor.fetchone()[0]
