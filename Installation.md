# Introduction #

ANDP has not yet been widely deployed, and documentation is still sparse. It does, however, work quite well under controlled circumstances on Ubuntu 7.10.

This pages briefly summarises which packages to install and which configuration files to change. Hardware-wise you will need a computer running Linux and one or more Dreambox tuners.

Contributions are welcome, especially in the area of documentation.

# Required software #

Install the following packages and their dependencies (e.g. using apt-get):

  * apache2
  * libapache2-mod-python
  * postgresql-plpython
  * python-imaging
  * python-ldap
  * python-psycopg2
  * python-tz

You will also need [python-xmltv](http://www.funktronics.ca/python-xmltv/), which must probably be installed manually.

# Installing ANDP #

Pre-compiled versions of ANDP are currently not available. Instead download the source code, as described on [the project page](http://code.google.com/p/andp/source/checkout).

The examples below assume that ANDP has been placed within `/usr/local/andp`.

Make sure that ANDP's modules are placed where Python can find them, e.g. by doing a `sudo ln -s /usr/local/andp/python/andp /usr/lib/python2.5/site-packages/`

# Configuring Apache #

Enable the required Apache modules:

```
sudo a2enmod mod_python
sudo a2enmod rewrite
```

Your `/etc/apache2/sites-available/default` file should look something like this:

```
NameVirtualHost *:80
<VirtualHost *:80>
  ServerAdmin webmaster@yoursite.example.com

  DocumentRoot /var/www/tv

  PythonOption andpConfigPath /usr/local/andp/config/tv.cfg

  <Directory />
    Options FollowSymLinks
    AllowOverride None
  </Directory>
  <Directory /var/www/tv/>
    Options None
    AllowOverride None
    Order allow,deny
    allow from all
  </Directory>
  <Directory /usr/local/andp/python/mod_python/>
    AddHandler python-program .py
    PythonHandler handler
    PythonDebug On
  </Directory>
  <Directory /usr/local/andp/data/img/>
    Options None
  </Directory>

  <Directory /usr/local/andp/data/css/>
    Options None
  </Directory>

  <Directory /usr/local/andp/data/cortado/>
    Options None
  </Directory>

  <Directory /mnt/tv/andp/>
    Options None
  </Directory>

  RewriteEngine on
  RewriteRule ^/img/(.*) /usr/local/andp/data/img/$1 [L]
  RewriteRule ^/css/(.*) /usr/local/andp/data/css/$1 [L]
  RewriteRule ^/cortado/(.*) /usr/local/andp/data/cortado/$1 [L]
  RewriteRule ^/video/(.*) /mnt/tv/andp/$1 [L]
  RewriteRule ^(.*) /usr/local/andp/python/mod_python/andp.py/$1 [L]

  ErrorLog /var/log/apache2/error.log

  # Possible values include: debug, info, notice, warn, error, crit,
  # alert, emerg.
  LogLevel warn

  CustomLog /var/log/apache2/access.log combined
  ServerSignature Off
</VirtualHost>
```

# Creating the Postgres database #

Create the database by running the `/usr/local/andp/db/create_database.sh` script.

# Configuring ANDP itself #

ANDP has its own configuration file. It's easiest to begin by copying the included sample:

```
cd /usr/local/andp/config
cp template.cfg tv.cfg
```

Open 'tv.cfg' with your favorite editor. Please see the comments in the file for further details.

# Adding cron jobs #

ANDP uses cron to initate recordings. Add the following line to www-data's crontab (e.g. by running `sudo crontab -e -u www-data`):

```
* * * * * /usr/local/andp/python/scripts/cron_min.py /usr/local/andp/config/tv.cfg
```

# Configuring your Dreambox(es) #

ANDP supports an unlimited number of Dreamboxes. Make sure their web administration interface has been turned on, and that you the password on each Dreambox is the same as you entered in ANDP's configuration file.