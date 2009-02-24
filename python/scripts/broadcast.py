#! /usr/bin/python
# -*- coding: utf-8; -*-

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

    tuner.SwitchToChannel(booking.channelID)
    tsURL = tuner.GetTSURL()

    outBasePath = booking.GetBasePath(cfg)

    dirPath = os.path.split(outBasePath)[0]
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)

    if booking.record:
        cmd = ("vlc", "-I", "dummy", "%s" % tsURL, "--sout-all", "--sout-udp-ttl", "10", "--sout", "#duplicate{dst=standard{mux=ts,dst=%s,access=rtp},dst=standard{access=file,mux=ps,dst=%s.mpg}}" % (tuner.mcGroup, outBasePath))
    else:
        cmd = ("vlc", "-I", "dummy", "%s" % tsURL, "--sout-all", "--sout-udp-ttl", "10", "--sout", "#standard{mux=ts,dst=%s,access=rtp}" % tuner.mcGroup)

    # We'll loop and sleep instead of just sleep, so that we don't
    # have to create a signal handler. (Sleeping is necessary, since
    # this script is sometimes started a bit before
    # broadcasting/recording is actually supposed to begin.)
    while datetime.datetime.now(booking.startTime.tzinfo) < booking.startTime:
        time.sleep(0.1)

    stdOut = open(outBasePath + ".mpg.stdout", "w")
    stdErr = open(outBasePath + ".mpg.stderr", "w")

    proc = subprocess.Popen(cmd, stdout = stdOut, stderr = stdErr)

    then = time.time() # For calculating real duration of recording

    # Loop and sleep. Se above.
    while datetime.datetime.now(booking.endTime.tzinfo) <= booking.endTime:
        retCode = proc.poll()

        if retCode != None:
            break
        
        time.sleep(1)

    #conn = psycopg2.connect("dbname=%s user=%s" % (dbName, dbUser))
    #cursor = conn.cursor()

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
    
