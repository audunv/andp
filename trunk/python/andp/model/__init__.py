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

This package contains all classes and other code used to access
data. Always use the interfaces defined here - do not communicate
directly with the database.

"""

__all__ = ["users", "tuners", "bookings", "remote"]

import re, random, datetime

def ValidEmailAddress(s):
    """
    
    Returns true if s is a valid email address (according to RFC 2822)
    
    """

    P = re.compile(r'^[a-z0-9_\-][a-z0-9_\-\.]*@[a-z0-9\-\.]+\.[a-z]{1,4}$', re.I)

    try:
        localPart, hostPart = s.split("@")
    except ValueError:
        return False

    if len(localPart) > 64 or len(hostPart) > 255:
        return False

    if not P.search(s):
        return False

    return True

def RandomHexString(i):
    """

    Returns a random string of hexadecimal characters with length i

    """

    return "".join([random.choice("0123456789abcdef") for i in xrange(i)])

def RandomReadableString(i):
    """

    Returns a random string of letters and digits with length
    i. String does not include characters which are easily confused

    """

    return "".join([random.choice("abcdefghjkmnpqrstuvwxyz23456789") for i in xrange(i)])

def MXDateTimeToDateTime(mdt):
    """

    Converts an MXDateTime object to its standard DateTime equivalent

      * mdt: MXDateTime object
    
    """
    
    return datetime.datetime(mdt.year, mdt.month, mdt.day, mdt.hour, mdt.minute, mdt.second, tzinfo = pytz.timezone('UTC'))
