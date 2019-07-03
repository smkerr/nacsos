from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from utils.utils import *
from scoping.utils import utils
import os
from django.db import connection, transaction
from psycopg2.extras import *
import time
import subprocess
from django.conf import settings
import operator
#import scoping


@shared_task
def add(x, y):
    return x + y

# @shared_task
# def query_doc_category(qid,cid):
#     docs = Doc.objects.filter(query=)

@shared_task
def handle_update_tag(tid):
    t = Tag.objects.get(pk=tid)
    t.update_tag()
    return t.id

@shared_task
def order_dos(dos):
    dos = DocOwnership.objects.filter(pk__in=dos).order_by('id')
    for i in range(len(dos)):
        do = dos[i]
        do.order=i
    DocOwnership.objects.bulk_update(dos, ['order'])
    return dos

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
    technologies = Category.objects.filter(project_id=pid)
    for t in technologies:
        t.queries = t.query_set.count()
        tdocs = Doc.objects.filter(category=t).values_list('id',flat=True)
        itdocs = Doc.objects.filter(query__category=t,query__type="default").values_list('id',flat=True)
        t.docs = len(set(tdocs).intersection(itdocs))
        t.nqs = t.queries
        t.ndocs = t.docs
        t.save()
    return

@shared_task
def upload_docs(qid, update):
    print(upload_docs.request.id)
    from celery.task.control import  inspect
    i = inspect()
    s = i.reserved()
    a = i.active()
    list(flatten(list(a.values()) + list(s.values())))
    for t in flatten(list(a.values()) + list(s.values())):
        if "upload_docs" in t["name"]:
            if eval(t['args'])[0] == qid:
                if str(t['id']) != str(upload_docs.request.id):
                    print("already running!")
                    return qid
    q = Query.objects.get(pk=qid)
    q.doc_set.clear()
    q.upload_log = ""
    q.save()

    title = str(q.id)

    if q.query_file.name is '':
        fname = settings.QUERY_DIR+title+"/results.txt"
    else:
        fname = q.query_file.path

    print(q.title)

    if ".xml" in q.query_file.name.lower():
        r_count = utils.read_xml(q,update)

    elif ".RIS" in q.query_file.name or ".ris" in q.query_file.name:
        r_count = read_ris(q,update)

    elif ".csv" in q.query_file.name:
        print("CSV")
        r_count = utils.read_csv(q)

    elif q.database =="WoS":
        print("WoS")
        with open(fname, encoding="utf-8") as res:
            if q.wos_db is not None and q.wos_db is not '':
                from django.db import connection
                connection.close()
                r_count = read_wos(res, q, update, deduplicate=True)
            else:
                r_count = read_wos(res, q, update)

    else:
        print("Scopus")
        if q.query_file.name is '':
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

    t.update_tag()


    return(q.id)

@shared_task
def download_metacodes(pid):
    return

@shared_task
def do_query(qid, background=True, dis=False):
    q = Query.objects.get(pk=qid)
    q.doc_set.clear()

    def arg_docs(arg):
        sq = Query.objects.get(pk=arg.strip())
        q.queries.add(sq)
        ds = Doc.objects.filter(query=sq)
        return set(ds.values_list('pk',flat=True))
    # Do internal queries
    if q.database=="intern":

        pat = re.compile('(AND|OR|NOT)',re.IGNORECASE)
        els = re.split(pat, q.text)
        args = els[2::2]
        ops = [o.strip().upper() for o in els[1::2]]

        docs = arg_docs(els[0])

        op_dict = {
            "AND": operator.and_,
            "OR": operator.or_,
            "NOT": operator.sub,
        }

        for arg, op in zip(args,ops):
            docs = op_dict[op](docs, arg_docs(arg))

        t = Tag(
            title="all",
            text="all",
            query=q
        )
        t.save()

        Through = Doc.query.through
        dqs = [Through(doc_id=d,query=q) for d in docs]
        Through.objects.bulk_create(dqs)

        Through = Doc.tag.through
        dts = [Through(doc_id=d,tag=t) for d in docs]
        Through.objects.bulk_create(dts)

        q.r_count = len(docs)
        q.save()
        t.update_tag()

    else:
        # write the query into a text file
        fname = q.txtfile()
        with open(fname,encoding='utf-8',mode="w") as qfile:
            qfile.write(q.text.encode("utf-8").decode("utf-8"))

        time.sleep(1)

        args = [
            "/home/galm/software/django/tmv/venv/bin/python3",
            "/home/galm/software/scrapewos/bin/scrapeQuery.py",
            "-s",
            q.database
        ]

        if dis:
            args += ["-dis", "True"]

        if q.creator.username in ["galm","khat","hilj","lamw","minj"]:
            args += ["-lim", "2000000"]
        if q.credentials:
            args += [
                "-cred_uname",q.creator.profile.cred_uname,
                "-cred_pwd", q.creator.profile.cred_pwd,
                "-cred_org", q.creator.profile.cred_org,
                "-credentials", "True"
            ]

        if q.collections:
            args += [
                "-collections", q.collections
            ]

        if q.wos_db:
            args += [
                "-wos_db", q.wos_db
            ]

        args+=[fname]

        print(args)

        print(" ".join(args))

        # run "scrapeQuery.py" on the text file in the background
        if background:
            subprocess.Popen(args)
        else:
            subprocess.call(args)

    return qid
