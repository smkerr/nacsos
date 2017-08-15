from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *

@shared_task
def add(x, y):
    return x + y

@shared_task
def update_projs(pids):

    projs = Project.objects.filter(id__in=pids)
    for p in projs:
        p.queries = p.query_set.distinct().count()
        p.docs = Doc.objects.filter(query__project=p).distinct().count()
        p.save()
    return(projs)
