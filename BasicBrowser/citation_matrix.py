import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import numpy as np

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
def doc_cites(doc):
    django.db.connections.close_all()
    citations = doc.wosarticle.cr
    cdos = []
    for c in citations:

        doim = re.findall("DOI ([0-9]+.*)",c)
        if len(doim) > 0:
            doi = doim[0].replace(" ","")
            cobject, created = Citation.objects.get_or_create(
                doi = doi
            )
            if created:
                cobject.ftext = c
                cobject.save()
            #otherise append to alt text
        else:
            cobject, created = Citation.objects.get_or_create(
                ftext = c
            )

        cdo = CDO(doc=doc,citation=cobject)
        cdos.append(cdo)
    return(cdos)


def main():
    qid = sys.argv[1]
    q = Query.objects.get(pk=qid)
    docs = Doc.objects.filter(
        query=q,
        wosarticle__cr__isnull=False,
        cdo__citation__isnull=True
    )

    docs = docs

    ndocs = docs.count()

    print(ndocs)

    # Chunk size, so as to prevent overuse of memory
    chunk_size = 1

    for i in range(ndocs//chunk_size+1):
        cdos = []
        f = i*chunk_size
        print(f)
        l = (i+1)*chunk_size
        if l > ndocs:
            l = ndocs-1
        chunk_docs = docs[f:l]
        pool = Pool(processes=1)
        cdos.append(pool.map(doc_cites,chunk_docs))
        pool.terminate()
        gc.collect()


        django.db.connections.close_all()
        cdos = flatten(cdos)

        CDO.objects.bulk_create(cdos)




if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
