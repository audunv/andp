-- Copyright (C) 2009 Østfold University College
-- 
-- This file is part of ANDP.
-- 
-- ANDP is free software; you can redistribute it and/or modify it
-- under the terms of the GNU General Public License as published by
-- the Free Software Foundation; either version 2 of the License, or
-- (at your option) any later version.
-- 
-- This program is distributed in the hope that it will be useful, but
-- WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
-- General Public License for more details.
-- 
-- You should have received a copy of the GNU General Public License
-- along with this program; if not, write to the Free Software
-- Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
-- 02111-1307, USA.

insert into users values('audunv', 'Audun Vaaler', 'audun.vaaler@hiof.no');
insert into channels values('bbc', 'BBC World', 'Tullenor', 't');
insert into tuners values('tuner1.hiof.no');
insert into tuners values('tuner1.hiof.no');
insert into tuners values('tuner2.hiof.no');
insert into tunerchannels values('tuner1.hiof.no', 'bbc');
insert into tunerchannels values('tuner2.hiof.no', 'bbc');

-- Error
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T11:00', '2007-01-15T11:15', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');

-- Success
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T11:00', '2007-01-16T11:15', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');

-- Various
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T10:00', '2007-01-16T10:15', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T12:00', '2007-01-16T12:15', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T10:55', '2007-01-16T11:00', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T10:55', '2007-01-16T10:59', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T11:15', '2007-01-16T11:30', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T11:15:01', '2007-01-16T11:30', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
 insert into reservations(startTime, endTime, channelID, tunerID, title, userName) values('2007-01-16T11:01', '2007-01-16T11:02', 'bbc', 'tuner1.hiof.no', 'World News', 'audunv');
