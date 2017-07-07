import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import numpy as np
from functools import partial

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def process_citation(c):
    x = x

def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

###################################
# function, to be done in parallel,
# which pull citations from docs,
# adds them to db,
# and links citations and docs
def bib_couple(cdoc,doc):
    bc, created = BibCouple.objects.get_or_create(
        doc1=doc,
        doc2=cdoc.doc
    )
    bc.cocites +=1
    bc.save()


def main():
    qid = sys.argv[1]
    q = Query.objects.get(pk=qid)
    docs = Doc.objects.filter(
        query=q,
        wosarticle__cr__isnull=False
    )
    time.sleep(7200)
    print("WOKE")
    django.db.connections.close_all()
    BibCouple.objects.all().delete()

    searchdocs=docs
    for d in docs.iterator():
        searchdocs = searchdocs.exclude(UT=d.UT)
        dcitations = Citation.objects.filter(cdo__doc=d)
        cdocs = CDO.objects.filter(
            doc__in=searchdocs,
            citation__in=dcitations
        )
        for cdoc in cdocs:
            bib_couple(cdoc,d)




if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
