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

This module defines classes, functions and database tables for
manipulating users. Also includes authentication functions.

"""

import time, random, urllib

import psycopg2

import ldap

import md5

import andp.exceptions

from andp.db import PsE

class User(object):
    """
    
    Represents a user
    
    """
    
    def __init__(self, username, fullName, email, admin = False):
        self.username = username
        self.fullName = fullName
        self.email    = email
        self.admin    = admin

    def LogOut(self, cursor, sessionID):
        """

        Log user out of tikktikk.com

          * sessionID: ID of session that should be terminated
        
        """
        
        sql = "delete from sessions where id=%s"

        PsE(cursor, sql, (sessionID,))

def GetUser(cursor, sessionID):
    """

    Returns User object corresponding to sessionID
    
    """
    
    PsE(cursor, "select u.username, u.fullName, u.email, u.admin from users u, sessions s where s.id=%s and u.username = s.username;", (sessionID,))
    res = cursor.fetchone()

    if res == None:
        return None
    else:
        username, fullName, email, admin = res

    return User(username, fullName, email, bool(admin))

def GetUsers(cursor, sortCol = "fullName", ascending = True, group = "all"):
    """

    Returns list of all users.

    """

    assert sortCol in ["fullName", "email", "admin", "username"]

    if ascending:
        sortDir = ""
    else:
        sortDir = " desc"
        
    if group == "all":
        groupSel = " "
    elif group == "admins":
        groupSel = " where admin = True "
    else:
        groupSel = " where admin = False "

    PsE(cursor, "select fullName, email, admin, username from users%sorder by %s%s;" % (groupSel, sortCol, sortDir))
    res = cursor.fetchall()

    return res

def AddAdminAccess(cursor, username):
    PsE(cursor, "update users SET admin = True where username = '%s';" % username)
    
    return cursor.statusmessage

def RemoveAdminAccess(cursor, username):
    PsE(cursor, "update users SET admin = False where username = '%s';" % username)

    return cursor.statusmessage


def GetUserByUsername(cursor, username):
    """

    USE WITH CAUTION

    Returns User object by username
    
    """
    
    PsE(cursor, "select fullName, email, admin from users where username=%s;", (username,))
    res = cursor.fetchone()

    if res == None:
        return None
    else:
        fullName, email, admin = res

    return User(username, fullName, email, bool(admin))

def ANDPpasswdAuthenticate(config, username, password):
    """
    Authentication against ANDP passwd file using MD5 hashes.

    Raises andp.exceptions.LoginFailed if no user or wrong password.
    """

    # Open and read htpasswdfile
    passfile = open(config["authentication"]["andppasswd"]["path"])
    unparsedUsers = passfile.readlines()
    passfile.close()

    # Parse htpasswdfile
    users = {}
    for user in unparsedUsers:
        userid, hash, email, name = unicode(user, 'utf-8').split(":")
        users[userid] = [hash, email, name]

    if username in users:
        hash, email, name = users[username]
        if md5.md5(password).hexdigest() != hash:
            raise andp.exceptions.LoginFailed
        return name, email

    raise andp.exceptions.LoginFailed

def LDAPAuthenticate(config, username, password):
    """
    Autentisering mot LDAP (Cerebrum)

    Avstedkommer andp.exceptions.LoginFailed hvis autentiseringen
    feilet. Returnerer ellers (navn, email).
    
    """

    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, config["authentication"]["ldap"]["certPath"])

    con = ldap.initialize(config["authentication"]["ldap"]["uri"])
    con.protocol_version = ldap.VERSION3
    con.set_option(ldap.OPT_X_TLS,ldap.OPT_X_TLS_DEMAND)
    dnBase = config["authentication"]["ldap"]["dnBase"]

    try:
        con.simple_bind_s("uid=" + username + "," + dnBase, password)
    except ldap.INVALID_CREDENTIALS:
        raise andp.exceptions.LoginFailed

    result = con.search_s(dnBase, ldap.SCOPE_SUBTREE, "(uid=%s)" % username, [config["authentication"]["ldap"]["nameLabel"], config["authentication"]["ldap"]["emailLabel"]])

    # Sjekk om ansatt eller staff:
    dn = "uid=%s,%s" % (username, dnBase)
    attrName = config["authentication"]["ldap"]["affiliation"]
    attrVals = config["authentication"]["ldap"]["groups"]
    
    allowedRole = False

    for attrVal in attrVals:
        if con.compare_s(dn, attrName, attrVal):
            allowedRole = True

    if not allowedRole:
        raise andp.exceptions.LoginFailed

    name = result[0][1]["cn"][0].decode("utf-8")
    email = result[0][1]["mail"][0]
    
    return name, email

def LogIn(config, conn, cursor, username, password):
    """

    Logs user in

      * username

      * password: User's password

    Raises andp.exceptions.LoginFailed if authentication failed.
    
    """
    
    # It's probably a good idea to sleep a little while to reduce the
    # rate at which someone can attempt logins. Adding a random
    # component should make it more difficult to pick up timing
    # patterns in our code. (*** Is this really sound?)    
    time.sleep(1 + random.random())

    # First make sure that user hasn't been blocked because of too many login attempts
    PsE(cursor, "select count(username) > 2 from FailedLogins where username=%s and time > (current_timestamp - interval '1 hours');", (username,))
    blocked = cursor.fetchone()[0]
    if blocked:
        raise andp.exceptions.TooManyLoginAttempts
    
    successfullAuthentication = False

    for method in config["authentication"]["modules"]:
        if method == "andppasswd":
            try:
                fullName, email = ANDPpasswdAuthenticate(config, username, password)
                info = "Wrong password or user does not exist!"
            except andp.exceptions.LoginFailed, info:
                fullName, email = ("","")
            if fullName != "":
                successfullAuthentication = True
                break

        elif method == "ldap":
            try:
                fullName, email = LDAPAuthenticate(config, username, password)
            except andp.exceptions.LoginFailed, info:
                fullName, email = ("","")

            if fullName != "":
                successfullAuthentication = True
                break

    if successfullAuthentication == False:
        # Login failed: Increase failed logins count and propagate the exception

        PsE(cursor, 'insert into FailedLogins (username) values (%s);', (username,))
        raise andp.exceptions.LoginFailed, info

    # Insert or update user info in the database
    try:
        PsE(cursor, "insert into users (username, fullName, email) values (%s, %s, %s);", (username.encode('utf-8'), fullName.encode('utf-8'), email.encode('utf-8')))
    except psycopg2.IntegrityError:
        # User already exists: We need to update only
        conn.rollback()
        PsE(cursor, "update users set fullName=%s, email=%s where username=%s", (fullName.encode('utf-8'), email.encode('utf-8'), username.encode('utf-8')))
    
    sessionID = andp.model.RandomHexString(32)
    PsE(cursor, "insert into sessions (id, username) values (%s, %s);", (sessionID, username))

    return sessionID
