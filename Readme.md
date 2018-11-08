

This is a fork of Allison J.B Chaney's **tmv** repository described below which has spread into doing
other things. Multiple topic models are managed, and linked to a database of documents (included in the **scoping** app). This scoping app deals with importing documents, and reviewing the documents for relevance in teams. This is run in the context of a research institute doing systematic reviews and other forms of evidence synthesis. Many parts of the repository are therefore specific to this context, and refer to specific bits of software that have institution-specific uses, but some attempt has been made to generalise, and this is an ongoing process.

The repository also contains apps for managing data from parliamentary protocols and twitter.

Refer to the [documentation](https://github.com/mcallaghan/tmv/wiki/Scoping-Documentation) for a (partial) guide to using the app.


## A general guide to installation

The following instructions assume installation on Ubuntu (18). Consult the internet for setting up PostgreSQL and Python/pip in other environments.

### Setting up PostgreSQL

If you do not have PostgreSQL installed already, install it. At time of writing, the latest release was PostgreSQL 10. This version is assumed. We also need postgis to handle geographical data

```
sudo apt update
sudo apt install postgresql postgresql-contrib postgis
```

Log on as the postgres user and start PostgreSQL
```
sudo -u postgres  -i
psql
```

Create a new user for this app (call it whatever you like), use a secure password, in single quotes:
```
CREATE USER scoper WITH PASSWORD 'secure_password';
```

Create a database for the app, use whatever name you like:
```
CREATE DATABASE scoping_tmv OWNER scoper;
```

Connect to the database and create a postgis extension

```
\connect scoping_tmv_legacy;
CREATE EXTENSION postgis;
```

Quit PostgreSQL and log out of the postgres user role

```
\q
exit
```

### Setting up Celery
We use celery to execute computation-heavy tasks in the background.
To do this we need to install the *message broker* RabbitMQ

```
sudo apt-get install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

To start celery, run

```
celery -A config worker --loglevel=info
```

### Setting up scoping-tmv

Operating in a virtual environment is **highly** recommended

```
pip3 install --user virtualenvironment

virtualenv -p python3 venv

source venv/bin/activate
```

Quickly install some system-level dependencies that the python packages need. Depending on your system configuration, you may need to install further system packages if the pip installation runs into errors.

```
sudo apt-get install libfreetype6-dev libpq-dev python-cffi libffi6 libffi-dev libxml2-dev libxslt1-dev
```

Once in the environment (or out of it at your own peril), install dependencies. Use requirements/local.txt for a local environment, or requirements/production.txt for a production environment.

```
pip install -Ur requirements.txt
```

This can take a while...

Now you need to add the file `BasicBrowser/BasicBrowser/settings_local.py`, which will not be commited, as it contains your secret information. Copy the template below, replacing the secret information with your own.

```
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECRET_KEY

# Set debug true in development settings, and false in production
DEBUG = True

from fnmatch import fnmatch
class glob_list(list):
    def __contains__(self, key):
        for elt in self:
            if fnmatch(key, elt): return True
        return False

INTERNAL_IPS = glob_list([The ips to be marked as internal])


DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': PASSWORD,
        'HOST': 'localhost',
        'PORT': '',
    }
}

```

Create an admin user if using on a clean database

```
python manage.py createsuperuser
```

Now you should be done, and ready to run a local server

```
python manage.py runserver
```


---

ONLINE TOPIC MODEL VISUALIZATION

Allison J. B. Chaney
achaney@princeton.edu

(C) Copyright 2011-2014, Allison J. B. Chaney

This is free software, you can redistribute it and/or modify it under
the terms of the GNU General Public License.

The GNU General Public License does not permit this software to be
redistributed in proprietary programs.

This software is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

------------------------------------------------------------------------
DESCRIPTION

This code uses the Django web framework [https://www.djangoproject.com],
which will need to be installed. On Unix systems, this can be done with:

    sudo pip install Django
    currently requires 1.2.4

The BasicBrowser is an interface that lazily generates pages to display
the results of a topic model.  Since each page querys the database, the
browser can keep pace with online topic models, displaying current data.
It can also be used with topic models that are not online.

------------------------------------------------------------------------
INCLUDED FILES

* BasicBrowser: a directory containing an online topic model browser,
    written in Python using the Django framework.
    * static: directory containing javascript, css, image files
    * templates: directory containing template html files with Django
        tags and filters
    * tmv_app: directory containing models and views files for the browser
        (see Django doc for more details)
    * db.py: a file to control writes to the database; this is generally
        the file imported into external topic model source (see wiki example)
    * all other .py files that come standard with Django (see Django doc
        for details)
* onlinewikipedia.py: a modified version of the Python script that comes
    with Online LDA (see below for source)
* Readme.txt: This file.
* COPYING: A copy of the GNU public license version 3.

------------------------------------------------------------------------
WIKIPEDIA DEMO

A demonstration of this browser can be run with the Wikipedia demo
included with the Online LDA source:

    http://www.cs.princeton.edu/~blei/downloads/onlineldavb.tar

If you are not familiar with the Online LDA source, it is recommended that
you read its readme and explore its demo before proceeding.

To run the browser with the Wikipedia demo, substitute the original
[onlinewikipedia.py] file with provided replacement. For example:

    cp online-tmve/onlinewikipedia.py onlineldavb/onlinewikipedia.py

All paths to the database need to be absolute, so modify the following
lines accordingly.

    onlinewikipedia.py, line 27
    BasicBrowser/settings.py, line 15

Finally, before running the demo, the database needs to be created.  In
the BasicBrowser directory, run

    python manage.py syncdb

At this point the Online LDA demo can be run as specified in its readme, e.g.

    python onlinewikipedia.py 101

to run the algorithms for 101 iterations (which isn't very long).

To view the browser, run the following in the BasicBrowser directory:

    python manage.py runserver

and navigate to the following link in a web browser, reloading as desired.
(The topics make take a while to be created and populated with terms.)

    http://127.0.0.1:8000/topic_presence

Viewing a given page of the browser make take longer while the topic model
is running than it does after the run completes.

If you want to start over again, remove the database file, sync the database
again before restarting the model.

    rm tmv_db; python manage.py syncdb

To install the browser on a web server, see the Django documentation.

------------------------------------------------------------------------
USING THE BROWSER WITH OTHER TOPIC MODELS

The browser can be used for any topic model, even if the model is not online.
For algorithms written in Python, simply import the db.py file and use its
functions to write to the database.  For algorithms not written in Python,
you need only write your data to the database, which can be done directly
with sqlite3, by embeding the db.py file in your code, or by using any other
method that works for you.  If you have the output of a model in a file, it
might be easiest to write a python script to transfer that data using db.py.
It shoudl be noted that as written, db.py uses a separate thread for most
writes to the database; this may not be ideal for all applications.
