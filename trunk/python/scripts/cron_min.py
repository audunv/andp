#! /usr/bin/python
# -*- coding: utf-8; -*-

"""

cron script that should be run every minute

"""

import sys, datetime, psycopg2, subprocess, os, signal

import andp.config

import andp.model.tuners
import andp.model.bookings

def StartUpcoming(cfgPath, cfg, cursor):
    # Pick bookings that are waiting and must start in less than 60 seconds
    bookings = [u for u in andp.model.bookings.GetBookings(cursor, 'w') if u.startTime - datetime.datetime.now(u.startTime.tzinfo) < datetime.timedelta(0, 60)]

    scriptPath = os.path.join(cfg["path"]["scripts"], "broadcast.py")

    for booking in bookings:
        cmd = "%s %s %s &" % (scriptPath, cfgPath, booking.id)
        proc = subprocess.Popen(cmd, shell = True)
    
def Main():
    cfgPath   = sys.argv[1]

    cfg = andp.config.Load(cfgPath)

    dbName = cfg["database"]["name"]
    dbUser = cfg["database"]["webUser"]

    conn = psycopg2.connect("dbname=%s user=%s" % (dbName, dbUser))
    cursor = conn.cursor()

    StartUpcoming(cfgPath, cfg, cursor)

if __name__ == "__main__":
    Main()
    
