#! /bin/bash

pg_dump andp > /tmp/andp_`date +'%Y%m%d_%H%M%S'`.sql && pg_dump --data-only andp > /tmp/andp-migrate.sql && dropdb andp && ./create_database.sh && psql andp < /tmp/andp-migrate.sql && rm -f /tmp/andp-migrate.sql
