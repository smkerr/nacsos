import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

from django.utils import timezone
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from django.conf import settings
from scoping.models import *
from scoping.views import *

def main():

    # Get technology ID from kwargs
    tid  = sys.argv[1] # Query containing list of documents
    # Get all the technology relevant docs (scopus)
    tech, docs, tobj = get_tech_docs(tid)
    docs = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech,
        scopus=True,
        wosarticle__di__iregex='\w'
    )

    dois = docs.values_list('wosarticle__di',flat=True)
    qtext = 'DOI("' + '" OR "'.join(dois) + '")'


    # Scrape them (and wait)
    q = Query(
        title=tobj.name+"_backward_1_1",
        database="scopus",
        type='backward',
        text=qtext,
        date=timezone.now(),
        step=1,
        substep=1,
        technology=tobj
    )
    q.save()
    fname = f"{settings.QUERY_DIR}{q.id}.txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)

    subprocess.Popen(["python3",
        "/home/galm/software/scrapewos/bin/scrapeQuery.py",
        "-s", "scopus", fname
    ]).wait()

    query_b2 = Query(
        title=str.split(q.title, "_")[0]+"_backward_"+str(q.step)+"_"+str(q.substep+1),
        database=q.database,
        type="backward",
        text="",
        date=timezone.now(),
        snowball=q.snowball,
        step=q.step,
        substep=q.substep+1
    )
    query_b2.save()

    subprocess.Popen(["python3",
        "/home/galm/software/tmv/BasicBrowser/proc_docrefs_scopus.py",
        str(q.id), str(query_b2.id), '0', '0'
    ]).wait()

    query_b2 = Query.objects.get(pk=query_b2.pk)

    fname = settings.QUERY_DIR+str(query_b2.id)+".txt"
    with open(fname,"w") as qfile:
        qfile.write(query_b2.text)

    subprocess.Popen(["python3",
        "/home/galm/software/scrapewos/bin/scrapeQuery.py",
        "-s", "scopus", fname
    ]).wait()

    subprocess.Popen(["python3",
        "/home/galm/software/tmv/BasicBrowser/proc_docrefs_scopus.py",
        str(q.id), str(query_b2.id), '0'
    ]).wait()

    # go through upload_docrefs_scopus, without adding, only saving text of ones
    # that are not in db.

    # filter for query matchers

    # Check for nodb refs

    # save them somewhere

    # Page says waiting, or lists these refs

if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
