# NACSOS: NLP Assisted Classification, Synthesis and Online Screening

Authors: Max Callaghan, Jérôme Hilaire, Finn Müller-Hansen, Yuan Ting Lee

## Summary

NACSOS is a django site for managing collections of documents, screening or coding them by hand, and doing NLP tasks with them like topic modelling or classifiation.

It was built for handling collections of scientific document metadata, but has extensions that deal with twitter data and parliamentary data.

It currently contains many experimental, redundant or unsupported features, and is not fully documented.

The part that deals with topic modelling is a fork of Allison J.B Chaney's **tmv** [repository](https://github.com/blei-lab/tmv). It extends this by managing multiple topic models and linking these with various document collections.

NACSOS is research software produced by the APSIS working group at the Mercator Research Institute on Global Commons and Climate Change ([MCC](https://www.mcc-berlin.net/)), and some parts of the repository are instution specific. We are in an ongoing process of generalising, and documenting.

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

Create a trigram extension

```
CREATE EXTENSION pg_trgm;
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
