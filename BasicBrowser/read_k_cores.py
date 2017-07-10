import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import numpy as np
from functools import partial
from scipy.sparse import coo_matrix, csr_matrix, find, tril
import networkx as nx

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def main():
    qid = sys.argv[1]
    q = Query.objects.get(pk=qid)

    mdocs = Doc.objects.filter(
        query=q,
        wosarticle__cr__isnull=False
    )

    m = mdocs.count()

    rev_m_dict = dict(zip(
        list(range(m)),
        list(mdocs.values_list('UT',flat=True))
    ))

    del mdocs

    print(Doc.objects.get(pk=rev_m_dict[0]))

    with open("/home/galm/projects/sustainability/networks/1366_5_k_cores.txt","r") as f:
        for line in f:
            fields = line.split()
            try:
                d = Doc.objects.get(pk=rev_m_dict[int(fields[0])])
                d.k = fields[1]
                d.save()
            except:
                print(fields)

if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
