from __future__ import absolute_import

import os
from celery import Celery
from kombu import Exchange, Queue, binding
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BasicBrowser.settings')

app = Celery(
    'BasicBrowser',
    #backend='redis://localhost:6379/0',
    #broker='redis://localhost:6379/0'
    broker=settings.BROKER_URL
)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

default_exchange = Exchange('default', type='direct')
long_exchange = Exchange('long', type='direct')
leey_exchange = Exchange('leey', type='direct')
muef_exchange = Exchange('muef', type='direct')


app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('long', long_exchange, routing_key='long'),
    Queue('leey', leey_exchange, routing_key='leey'),
    Queue('muef', muef_exchange, routing_key='muef')
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# increase visibility timeout such that long tasks are not scheduled multiple times
app.conf.broker_transport_options = {'visibility_timeout': 129600}  # 43200 s = 12 h, 129600 s = 36 h

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

# celery multi start -A BasicBrowser worker -l info -Q default --concurrency=4; celery multi start -A BasicBrowser longworker -l info -Q long --concurrency=2; celery multi start -A BasicBrowser mediumworker -l info -Q medium --concurrency=2
