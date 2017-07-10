import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import numpy as np
from functools import partial
from scipy.sparse import coo_matrix, csr_matrix, find, tril

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

def main():
    qid = sys.argv[1]
    q = Query.objects.get(pk=qid)
    docs = Doc.objects.filter(
        query=q,
        wosarticle__cr__isnull=False,
        cdo__citation__isnull=True
    )

    




if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
