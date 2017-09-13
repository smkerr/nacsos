from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BasicBrowser.settings')

app = Celery(
    'BasicBrowser',
    backend='redis://localhost:6379/0',
    broker='redis://localhost:6379/0'
)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
