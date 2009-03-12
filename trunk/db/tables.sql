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

-- Create hex-encoded random strings of arbitrary length.
create function RandomHexString(int)
returns char as
'import andp.model; return andp.model.RandomHexString(args[0])'
language plpythonu;

-- Users. Since we can't look up these details every time (for
-- performance reasons and since we'd need passwords) they are
-- cached here every time user logs on
create table Users (
  username varchar(16) primary key,
  fullName varchar(64), -- user's real name
  email varchar(320) not null,
  admin boolean default 'f' not null -- if true, user is allowed to use the web administration interface
);

create table FailedLogins (
  username varchar(16) not null,
  time timestamp with time zone not null default current_timestamp
);

create table Sessions (
  id char(32) primary key default RandomHexString(32),
  time timestamp with time zone not null default current_timestamp,
  username varchar(16) references Users on delete cascade not null
);

-- Tuners
create table Tuners (
  id varchar(64) primary key     -- tuner's DNS host name or IP address
);

-- Channels
create table Channels (
  id varchar(64) primary key,    -- channel ID (as used internally by Dreambox)
  name varchar(64) not null,     -- name to display to users
  provider varchar(64) not null, -- name of provider (e.g. Telenor)
  enabled boolean default 'f'    -- whether channel should be listed
);

-- Many-to-many relation between tuners and channels
create table TunerChannels (
  tunerID varchar(64) references Tuners on delete cascade,
  channelID varchar(64) references Channels on delete cascade,
  primary key(tunerID, channelID)
);

-- Booking states:
--   e: error
--   f: finished
--   i: in progress
--   w: waiting

-- Bookings (both scheduled, ongoing and completed)
create table Bookings (
  id char(32)  primary key default RandomHexString(32),
  startTime    timestamp with time zone not null,
  endTime      timestamp with time zone not null,
  channelID    varchar(64) references channels, -- longest seen so far was 34
  tunerID      varchar(64) references Tuners, -- allocated tuner
  record       boolean default 'f', -- true if program should be recorded to disk
  state	       char(1) check(state = 'e' or state = 'f' or state = 'i' or state = 'w') not null default 'w',
  notice       varchar(16384), -- optional notice to show to user (e.g. error message)
  title	       varchar(64) not null, -- user's booking title
  description  varchar(512), -- user's description
  username     varchar(16) not null references Users, -- username
  realDuration float, -- actual duration of a finished recording, in seconds

  -- Checks:
  --
  --   * End time must be later than start time for bookings that are waiting or in progress
  --   * Maximum duration is 12 hours
  --   * Bookings that are waiting or in progress must have an associated tuner
  check (startTime < endTime),
  check (endTime > current_timestamp or state='f' or state='e'),
  check (endTime - startTime < '12 hours'::interval),
  check (tunerID is not null or state='e' or state='f')
);

-- tuner ID, start time, end time, booking id
create function IsTunerAvailable(varchar, timestamp with time zone, timestamp with time zone, char)
returns boolean as '

  select count(id) < 1
  from bookings
  where tunerID = $1
  and id != $4
  and (($2 >= startTime and $2 <= endTime) or  ($3 >= startTime and $3 <= endTime));

' language sql;

-- channel id, start time, end time
create function GetAvailableTuners(varchar, timestamp with time zone, timestamp with time zone, char)
returns varchar as '

  select t.id from Tuners as t, TunerChannels as tc
  where tc.channelID = $1
  and t.id = tc.tunerID
  and IsTunerAvailable(t.id, $2, $3, $4);

' language sql;

-- Add tuner availability check (we can't do it inside create table)
alter table Bookings
add check(IsTunerAvailable(tunerID, startTime, endTime, id));

-- Permissions
grant select, insert, update on Users to "www-data";
grant select, insert, update, delete on FailedLogins to "www-data";
grant select, insert, update, delete on Sessions to "www-data";
grant select, insert, update, delete on Tuners to "www-data";
grant select, insert, update, delete on Channels to "www-data";
grant select, insert, update, delete on TunerChannels to "www-data";
grant select, insert, update, delete on Bookings to "www-data";

-- Indexes
create index ChannelAndStartTimeIndex on Bookings (channelID, startTime);
