#! /usr/bin/python
# -*- coding: utf-8; -*-
# ANDP password file generator

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

import sys, md5, os.path, locale

import getpass

if __name__ == "__main__":
    if len(sys.argv) <= 4:
        print "Usage: andppasswd.py <passwdfile> <username> <e-mail> <full name>"
        sys.exit(1)

    if "".join(sys.argv[1:]).find(":") != -1:
        print 'Error: Invalid character ":"'
        sys.exit(1)

    filepath = sys.argv[1]
    username = sys.argv[2]
    email = sys.argv[3]
    fullName = unicode(sys.argv[4], "iso-8859-1")

    passwordSet = False

    while passwordSet == False:
        pass1 = getpass.getpass("\nPlease enter password: ")
        pass2 = getpass.getpass("Please confirm password: ")
        if pass1 == pass2:
            passwordSet = True
            password = pass1
        else:
            print ""
            print "Error: Passwords did not match. Please try again."

    hash = md5.md5(password).hexdigest()
    users = {}
    
    if os.path.exists(filepath):
        passfile = open(filepath)
        rawusers = passfile.readlines()
        passfile.close()

        for user in rawusers:
            if len(user) > 1:
                userid, uhash, uemail, uname = user.split(":")
                users[userid] = [uhash, uemail, uname]

    users[username] = [hash, email, fullName]

    passfile = open(filepath, "w")
    for user in users:
        uhash, uemail, uname = users[user]
        passfile.write("%s:%s:%s:%s\n" % (user, uhash, uemail, uname.strip().encode('utf-8')))
    passfile.close()
