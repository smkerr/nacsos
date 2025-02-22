"""
WSGI config for myproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BasicBrowser.settings')

import logging
from django.core.wsgi import get_wsgi_application
from django.conf import settings

logging.info(f'Using settings {settings.SETTINGS_MODULE!r}')
print(f'Using settings {settings.SETTINGS_MODULE!r}')

application = get_wsgi_application()
