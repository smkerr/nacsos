from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from utils.utils import *
import os
from django.db import connection, transaction
from psycopg2.extras import *
import time
import subprocess

@shared_task
def add(x, y):
    return x + y

# @shared_task
# def query_doc_category(qid,cid):
#     docs = Doc.objects.filter(query=)

@shared_task
def update_projs(pids,add_docprojects=False):

    projs = Project.objects.filter(id__in=pids)

    for p in projs:
        p.queries = p.query_set.distinct().count()
        p.docs = p.docproject_set.count()
        p.reldocs = p.docproject_set.filter(relevant=1).count()
        if add_docprojects:
            docs = set(list(Doc.objects.filter(query__project=p).values_list('pk',flat=True)))
            dps = [(d,p.id,0) for d in docs]
            cursor = connection.cursor()
            p.doc_set.clear()
            execute_values(
                cursor,
                "INSERT INTO scoping_docproject (doc_id, project_id, relevant) VALUES %s",
                dps
            )
        p.tms = len(set(list(RunStats.objects.filter(query__project=p).values_list('pk',flat=True))))
        p.save()
    return

@shared_task
def update_techs(pid):
    technologies = Technology.objects.filter(project_id=pid)
    for t in technologies:
        t.queries = t.query_set.count()
        tdocs = Doc.objects.filter(technology=t).values_list('id',flat=True)
        itdocs = Doc.objects.filter(query__technology=t,query__type="default").values_list('id',flat=True)
        t.docs = len(set(tdocs).intersection(itdocs))
        t.nqs = t.queries
        t.ndocs = t.docs
        t.save()
    return

@shared_task
def upload_docs(qid, update):
    q = Query.objects.get(pk=qid)

    title = str(q.id)

    if q.query_file.name is '':
        fname = "/queries/"+title+"/results.txt"
    else:
        fname = q.query_file.path

    print(q.title)

    if ".RIS" in q.query_file.name:
        r_count = read_ris(fname,q,update)

    if q.database =="WoS":
        print("WoS")
        with open(fname, encoding="utf-8") as res:
            r_count = read_wos(res, q, update)

    else:
        print("Scopus")
        fname = fname.replace('results','s_results')
        with open(fname, encoding="utf-8") as res:
            r_count = read_scopus(res, q, update)

    print(r_count)
    django.db.connections.close_all()
    q.r_count = r_count
    q.save()

    t = Tag(
        title="all",
        text="all",
        query=q
    )
    t.save()
    for d in q.doc_set.all().iterator():
        d.tag.add(t)

    return(q.id)

@shared_task
def do_query(qid):
    q = Query.objects.get(pk=qid)
    q.doc_set.clear()
    # Do internal queries
    if q.database=="intern":
        args = q.text.split(" ")
        # Original one for combining qs
        if "manually uploaded" in q.text:
            print("manually uploaded")
        elif args[1].strip() in ["AND", "OR", "NOT"]:
            q1 = set(Doc.objects.filter(query=args[0]).values_list('id',flat=True))
            op = args[1]
            q2 = set(Doc.objects.filter(query=args[2]).values_list('id',flat=True))
            if op =="AND":
                ids = q1 & q2
            elif op =="OR":
                ids = q1 | q2
            elif op == "NOT":
                ids = q1 - q2
            combine = Doc.objects.filter(id__in=ids)
        else:
            # more complicated filters
            if args[0].strip()=="*":
                q1 = Doc.objects.all()
                q1ids = None
                cids = q1ids
            else:
                q1 = Doc.objects.filter(query=args[0])
                q1ids = q1.values_list('id',flat=True)
                cids = q1ids
            for a in range(1,len(args)):
                parts = args[a].split(":")
                print(parts)
                # Deal WITH tech filters
                if parts[0] == "TECH":
                    tech, tdocs, tobj = get_tech_docs(parts[1])
                    tids = tdocs.values_list('id',flat=True)
                    if q1ids is not None:
                        cids = list(set(q1ids).intersection(set(tids)))
                    else:
                        cids = tids
                    q1ids = cids
                    combine = Doc.objects.filter(pk__in=cids)
                # Deal with relevance filters
                if parts[0] == "IS":
                    if parts[1] == "RELEVANT":
                        combine = Doc.objects.filter(
                            pk__in=cids,
                            docownership__relevant=1
                        ) | Doc.objects.filter(
                            pk__in=cids,
                            technology__isnull=False
                        )
                    if parts[1] == "TRELEVANT":
                        combine = Doc.objects.filter(
                            pk__in=cids,
                            docownership__relevant=1,
                            docownership__query__technology=tobj
                        ) | Doc.objects.filter(
                            pk__in=cids,
                            technology=tobj
                        )


        for d in combine.distinct('id'):
            d.query.add(q)
        q.r_count = len(combine.distinct('id'))
        q.save()

    else:
        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,encoding='utf-8',mode="w") as qfile:
            qfile.write(q.text.encode("utf-8").decode("utf-8"))

        time.sleep(1)
        # run "scrapeQuery.py" on the text file in the background
        if q.creator.username=="galm":
            subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-lim","200000","-s", q.database, fname])
        else:
            subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", q.database, fname])

    return qid
