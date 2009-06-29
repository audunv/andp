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

FILE_SIZE_LIMIT = 2 * 1024 * 1024 * 1024

import sys, time, datetime, psycopg2, subprocess, os, signal, stat, traceback

import andp.config

import andp.model.tuners
import andp.model.bookings

def SplitFile(sizeLimit, path):
    """

    Splits a file into pieces less than sizeLimit bytes long and
    deletes original file
    
    """

    # If file is smaller than limit, we just need to rename it
    if os.stat(path)[stat.ST_SIZE] < sizeLimit:
        base, ext = os.path.splitext(path)
        outPath = "%s_000%s" % (base, ext)

        os.rename(path, outPath)

        return

    inFile  = open(path, "rb")
    outFile = None

    outCount = 0
    numBytesWritten = 0

    while True:
        data = inFile.read(1024 * 1024)

        if not data:
            break
        
        if not outFile or numBytesWritten + len(data) >= sizeLimit:
            base, ext = os.path.splitext(path)
            outPath = "%s_%03i%s" % (base, outCount, ext)
            outFile = open(outPath, "wb")
            numBytesWritten = 0
            outCount += 1

        outFile.write(data)
        numBytesWritten += len(data)

    os.unlink(path)

def PerformBroadcast(cfg, conn, cursor, booking):
    """

    Everything that might generate exceptions should be performed
    here, so that Main() can tidily catch and log them.
    
    """

    booking.SetState(cursor, 'i')
    conn.commit()

    tuner = andp.model.tuners.GetTuner(cursor, cfg, booking.tunerID)

    assert booking.endTime > datetime.datetime.now(booking.endTime.tzinfo)

    ## Since this script might run for a long time, we'll keep database
    ## connection closed until we need it again
    #conn.commit()
    #cursor.close()
    #conn.close()
    #del cursor, conn

    outBasePath = booking.GetBasePath(cfg)

    if isinstance(booking.channel, andp.model.tuners.Channel):
        tuner.SwitchToChannel(booking.channel.id)
        uri = tuner.GetTSURL()

        if booking.record:
            cmd = ("vlc", "-I", "dummy", "%s" % uri, "--sout-all", "--sout-udp-ttl", "10", "--sout", "#duplicate{dst=standard{mux=ts,dst=%s,access=rtp},dst=standard{access=file,mux=ps,dst=%s.mpg}}" % (tuner.mcGroup, outBasePath))
        else:
            cmd = ("vlc", "-I", "dummy", "%s" % uri, "--sout-all", "--sout-udp-ttl", "10", "--sout", "#standard{mux=ts,dst=%s,access=rtp}" % tuner.mcGroup)
    else:
        uri = booking.channel.id

        if booking.record:
            cmd = ("vlc", "-I", "dummy", "%s" % uri, "--sout-all", "--sout", "#standard{access=file,mux=ps,dst=%s.mpg}" % (outBasePath,))
        else:
            cmd = None # Don't do nothing

    dirPath = os.path.split(outBasePath)[0]
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)

    # We'll loop and sleep instead of just sleep, so that we don't
    # have to create a signal handler. (Sleeping is necessary, since
    # this script is sometimes started a bit before
    # broadcasting/recording is actually supposed to begin.)
    while datetime.datetime.now(booking.startTime.tzinfo) < booking.startTime:
        time.sleep(0.1)

    stdOut = open(outBasePath + ".mpg.stdout", "w")
    stdErr = open(outBasePath + ".mpg.stderr", "w")

    if cmd:
        for item in cmd:
            open("/tmp/debug.txt", "a").write(item + " : ")
        proc = subprocess.Popen(cmd, stdout = stdOut, stderr = stdErr)

        then = time.time() # For calculating real duration of recording

        # Loop and sleep. Se above.
        while datetime.datetime.now(booking.endTime.tzinfo) <= booking.endTime:
            retCode = proc.poll()
            
            if retCode != None:
                break
            
            time.sleep(1)
            
        if retCode or datetime.datetime.now(booking.endTime.tzinfo) <= booking.endTime:
            # Early termination or return code != 0 indicates error
            booking.SetState(cursor, "e", "Return code was %i. Error occured at %s." % (retCode, datetime.datetime.now(booking.startTime.tzinfo)))
        else:
            now = time.time()
        
            os.kill(proc.pid, signal.SIGTERM)
            time.sleep(5)
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass

    # Only try to split file if we're actually recording
    if booking.record:
        SplitFile(FILE_SIZE_LIMIT, outBasePath + ".mpg")

        booking.SetState(cursor, 'f')
        booking.SetRealDuration(cursor, now - then) # Must be done after SetState (due to integrity checks)

    conn.commit()

def Main():
    cfgPath   = sys.argv[1]
    bookingID = sys.argv[2]

    cfg = andp.config.Load(cfgPath)

    dbName = cfg["database"]["name"]
    dbUser = cfg["database"]["webUser"]

    conn = psycopg2.connect("dbname=%s user=%s" % (dbName, dbUser))
    cursor = conn.cursor()

    booking = andp.model.bookings.GetBooking(cursor, bookingID)
    
    try:
        PerformBroadcast(cfg, conn, cursor, booking)
    except:
        excInfo = sys.exc_info()
        excInfoS = "".join(traceback.format_exception(excInfo[0], excInfo[1], excInfo[2]))
        booking.SetState(cursor, "e", "Python exception:\n\n%s" % str(excInfoS))
        conn.commit()
        
        raise

if __name__ == "__main__":
    Main()
    
