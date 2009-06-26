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

This module contains generic widgets for use on web pages.

A widget typically represents an input, and includes functionality for
parsing and validating data.

"""

import time, os, datetime

from mod_python import apache

import andp.view.web

class Widget(object):
    """

    Abstract base class for all widgets.

    """

    def __init__(self, parent, name, value = None):
        self.parent  = parent
        self.name    = name
        self.value   = value

    def ParseInput(self, form):
        """
        Parses form data, and returns tuple (status, data, message)

          status:  True if input data were valid, False otherwise
          data:    Parsed input data
          message: Optional error message to be displayed to end user.
                   Empty string if everything's OK
        """
        return (True, None, "")

class TimeWidget(Widget):
    """

    A widget that lets user select a time.
    
    """

    def __init__(self, parent, name, value = None):
        super(self.__class__, self).__init__(parent, name, value)

        if not self.value:
            self.value = time.localtime()[3:5]

    def GetHTML(self, form = None, ampm = False):
        if form:
            defHour = int(form.get(self.name + "_hour", ""))
            defMin  = int(form.get(self.name + "_min", ""))
            try:
                defAMPM = form[self.name + "_ampm"].value
            except KeyError:
                defAMPM = None
        else:
            if ampm:
                if self.value[0] < 12:
                    defHour, defMin = self.value
                    defAMPM = "am"
                else:
                    defHour = self.value[0] - 12
                    defMin  = self.value[1]
                    defAMPM = "pm"
            else:
                defHour, defMin = self.value
                defAMPM = False

        html = '<select name="%s_hour" id="%s_hour">' % (self.name, self.name)

        if ampm:
            upperHour = 12
        else:
            upperHour = 24
        
        for hour in xrange(0, upperHour):
            if ampm and hour == 0:
                showHour = 12
            else:
                showHour = hour
            
            if hour == defHour:
                html += '<option value="%02i" selected="1">%02i</option>' % (hour, showHour)
            else:
                html += '<option value="%02i">%02i</option>' % (hour, showHour)

        html += '</select>'

        html += ':'

        html += '<select name="%s_min" id="%s_min">' % (self.name, self.name)
        for mint in xrange(0, 60, 5):
            # In case we get a value that isn't a multiple of five (shouldn't happen)
            if mint == (defMin / 5) * 5:
                html += '<option value="%02i" selected="1">%02i</option>' % (mint, mint)
            else:
                html += '<option value="%02i">%02i</option>' % (mint, mint)
        html += '</select>\n'

        if ampm:
            html += '<select name="%s_ampm" id="%s_ampm">' % (self.name, self.name)
            for ampmTxt in ["am", "pm"]:
                if ampmTxt == defAMPM:
                    html += '<option value="%s" selected="1">%s</option>' % (ampmTxt, ampmTxt.upper())
                else:
                    html += '<option value="%s">%s</option>' % (ampmTxt, ampmTxt.upper())
            html += '</select>\n'            

        return html

    def ParseInput(self, form):
        try:
            hourS = form[self.name + "_hour"].value
            mintS = form[self.name + "_min"].value
        except KeyError:
            return (False, None, "You must specify a time")

        try:
            ampm = form[self.name + "_ampm"].value
        except KeyError:
            ampm = None
                
        try:
            hour = int(hourS)
            mint = int(mintS)
        except ValueError:
            return (False, None, "Invalid time")

        if ampm == "pm":
            hour += 12

        if hour < 0 or hour > 23 or mint < 0 or mint > 59:
            return (False, None, "Invalid time")

        return (True, (hour, mint, 0), "")

class DateWidget(Widget):
    """

    Allows user to select a date.
    
    """
    
    monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    shortMonthNames = [name[:3] for name in monthNames]

    def __init__(self, parent, name, value = None):
        super(self.__class__, self).__init__(parent, name, value)

        if not self.value:
            self.value = time.localtime()[:3]
        
    def GetHTML(self, form = None):
        if form:
            defYear  = int(form.get(self.name + "_year", ""))
            defMonth = int(form.get(self.name + "_month", ""))
            defDay   = int(form.get(self.name + "_day", ""))
        else:
            defYear, defMonth, defDay = self.value

        html = '<select name="%s_day" id="%s_day">\n' % (self.name, self.name)
        for day in xrange(1, 32):
            if day == defDay:
                html += '  <option value="%i" selected="1">%i</option>\n' % (day, day)
            else:            
                html += '  <option value="%i">%i</option>\n' % (day, day)
        html += '</select>\n'

        html += '<select name="%s_month" id="%s_month">\n' % (self.name, self.name)
        for i in xrange(len(self.monthNames)):
            monthName = self.monthNames[i]
            if i + 1 == defMonth:
                html += '  <option value="%i" selected="1">%s</option>\n' % (i + 1, monthName)
            else:
                html += '  <option value="%i">%s</option>\n' % (i + 1, monthName)
        html += '</select>\n'

        firstYear = time.gmtime(time.time() - 24 * 3600)[0]

        html += '<select name="%s_year" id="%s_year">\n' % (self.name, self.name)
        for year in xrange(firstYear, firstYear + 2):
            if year == defYear:
                html += '  <option value="%i" selected="1">%04i</option>\n' % (year, year)
            else:
                html += '  <option value="%i">%04i</option>\n' % (year, year)
        html += '</select>\n'

        return html

    def ParseInput(self, form):
        try:
            dayS   = form[self.name + "_day"].value
            monthS = form[self.name + "_month"].value
            yearS  = form[self.name + "_year"].value
        except KeyError:
            return (False, None, "You must specify a date")

        try:
            day   = int(dayS)
            month = int(monthS)
            year  = int(yearS)
        except ValueError:
            return (False, None, "Invalid date")

        if day < 1 or day > 31 or month < 1 or month > 12:
            return (False, None, "Invalid date")

        return (True, (year, month, day), "")

class SelectWidget(Widget):
    def __init__(self, parent, name, value = None, options = []):
        super(self.__class__, self).__init__(parent, name, value)

        self.options = options
        
    def GetHTML(self, form = None):
        if form:
            selected = form.get(self.name, None)
        else:
            selected = self.value

        html = '<select name="%s" id="%s">\n' % (self.name, self.name)
        for option, label in self.options:
            if option == selected:
                html += '  <option value="%s" selected="1">%s</option>\n' % (option, label)
            else:            
                html += '  <option value="%s">%s</option>\n' % (option, label)
        html += '</select>\n'

        return html

    def ParseInput(self, form):
        return (True, form[self.name].value, "")

class RadioWidget(Widget):
    def __init__(self, parent, name, value = None, options = []):
        super(self.__class__, self).__init__(parent, name, value)

        self.options = options
        
    def GetHTML(self, form = None):
        if form:
            selected = form.get(self.name, "")
        else:
            selected = self.options[0][0]

        inputs = []
        for option, label in self.options:
            if option == selected:
                inputs.append('<input type="radio" name="%s" value="%s" checked="1" />%s\n' % (self.name, option, label))
            else:            
                inputs.append('<input type="radio" name="%s" value="%s" />%s\n' % (self.name, option, label))

        return "\n<br/>".join(inputs)

    def ParseInput(self, form):
        return (True, form[self.name].value, "")

class TextWidget(Widget):
    """

    A simple one-line or multi-line textbox widget
    
    """
    
    def __init__(self, req, name, value = "", required = False, errMsg = "Field is required", maxLen = 64, cols = 20, rows = 1):
        super(TextWidget, self).__init__(req, name, value = value)

        self.required = required
        self.errMsg = errMsg
        self.maxLen = maxLen
        self.cols   = cols
        self.rows   = rows

    def GetHTML(self, form = None):
        EH = andp.view.web.EH

        if form:
            try:
                value = form[self.name].value
            except KeyError:
                value = self.value
        else:
            value = self.value

        if self.rows > 1:
            return '<textarea name="%s" cols="%i" rows="%i">%s</textarea>' % (self.name, self.cols, self.rows, EH(value))
        else:
            return '<input type="text" name="%s" value="%s" size="%i" />' % (self.name, EH(value), self.cols)

    def ParseInput(self, form):
        try:
            value = form[self.name].value
        except KeyError:
            value = ""

        if self.required and not value:
            return (False, None, self.errMsg)

        if len(value) > self.maxLen:
            return (False, None, 'Too long (max %i characters)' % self.maxLen)

        return (True, value, "")
