import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import scrapeWoS #import scopus2wosfields
from urllib.parse import urlparse, parse_qsl


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def shingle(text):
    return set(s for s in ngrams(text.lower().split(),2))

def get(r, k):
    try:
        x = r[k]
    except:
        x = ""
    return(x)

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0




def main():
    sdocs = Doc.objects.exclude(UT__contains="WOS:",wosarticle__di__isnull=True)
    for s in sdocs.iterator():
        docs = []
        py_docs = Doc.objects.exclude(UT=s.UT).filter(PY=s.PY)

        s1 = shingle(s.title)

        for d in py_docs:
            j = jaccard(s1,d.shingle())
            if j > 0.51:
                docs.append(d)

        if len(docs)>1:
            print("{} matches the following:".format(s.title))
            for d in docs:
                print(d.title)
            break



if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
