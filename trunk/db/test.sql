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
