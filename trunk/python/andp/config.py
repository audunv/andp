#! /usr/bin/python
# -*- coding: utf-8 -*-

"""

This module contains a function used to read configuration files

"""

def Load(path):
    """
    Reads config file and returns dictionariy of settings.

      * path: Path to config file
      
    """

    #authentication = {
    #    "andppasswd": {},
    #    "ldap": {}
    #    }
    
    d = {
        "network":  {},
        "path":     {},
        "database": {},
        "session":  {},
        "email":    {},
        "debug":    {},
        "tuners":   {},
        "authentication": { "andppasswd": {}, "ldap": {}},
        "web":      {},
        }

    execfile(path, globals(), d)

    return d
