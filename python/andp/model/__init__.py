# -*- coding: utf-8; -*-

"""

This package contains all classes and other code used to access
data. Always use the interfaces defined here - do not communicate
directly with the database.

"""

__all__ = ["users", "tuners", "bookings"]

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

    Returns a random string of hexadecimal characters of length i

    """

    return "".join([random.choice("0123456789abcdef") for i in xrange(i)])

def MXDateTimeToDateTime(mdt):
    """

    Converts an MXDateTime object to its standard DateTime equivalent

      * mdt: MXDateTime object
    
    """
    
    return datetime.datetime(mdt.year, mdt.month, mdt.day, mdt.hour, mdt.minute, mdt.second, tzinfo = pytz.timezone('UTC'))
