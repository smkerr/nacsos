from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from utils.utils import *
import os

@shared_task
def add(x, y):
    return x + y

@shared_task
def update_projs(pids):

    projs = Project.objects.filter(id__in=pids)
    for p in projs:
        p.queries = p.query_set.distinct().count()
        p.docs = len(set(list(Doc.objects.filter(query__project=p).values_list('pk',flat=True))))
        p.tms = len(set(list(RunStats.objects.filter(query__project=p).values_list('pk',flat=True))))
        p.save()
    return

@shared_task
def upload_docs(qid, update):
    q = Query.objects.get(pk=qid)

    print(q.title)

    title = str(q.id)

    if q.database =="WoS":
        print("WoS")
        with open("/queries/"+title+"/results.txt", encoding="utf-8") as res:
            r_count = read_wos(res, q, update)

    else:
        print("Scopus")
        with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
            r_count = read_scopus(res, q, update)

    print(r_count)
    django.db.connections.close_all()
    q.r_count = r_count
    q.save()
