from __future__ import absolute_import

import os
from celery import Celery
from kombu import Exchange, Queue, binding
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BasicBrowser.settings')

app = Celery(
    'BasicBrowser',
    backend='redis://localhost:6379/0',
    broker='redis://localhost:6379/0'
)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

default_exchange = Exchange('default', type='direct')
medium_exchange = Exchange('medium', type='direct')
long_exchange = Exchange('long', type='direct')

app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('medium', medium_exchange, routing_key='long'),
    Queue('long', long_exchange, routing_key='long'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

# celery multi start -A BasicBrowser worker -l info -Q default --concurrency=4; celery multi start -A BasicBrowser longworker -l info -Q long --concurrency=2; celery multi start -A BasicBrowser mediumworker -l info -Q medium --concurrency=2
