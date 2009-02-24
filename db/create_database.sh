#! /bin/bash

createuser --no-adduser --no-createdb www-data
createdb --encoding utf-8 andp

createlang plpythonu andp

psql andp < tables.sql
