import os, sys, time, resource, re, gc, shutil
from nltk import ngrams
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *



def shingle_doc(i,k):
    django.db.connections.close_all()
    doc = Doc.objects.all()[i]
    text = doc.title
    
    text = text.lower()
    shingleLength = k
    tokens = text.split()

    shingles = [tokens[i:i+shingleLength] for i in range(len(tokens) - shingleLength + 1) if len(tokens[i]) < 4]
    shingles = ngrams(tokens,k)
    s_set = set()
    for s in shingles:
        shingle = TitleShingle(
            doc = doc,
            s1 = s[0],
            s2 = s[1]
        )
        shingle.save()
    django.db.connections.close_all()

def main():
      
    TitleShingle.objects.all().delete()

    wos_docs_i = range(Doc.objects.all().count())

    #wos_docs_i = range(10)

    pool = Pool(processes=8)
    pool.map(partial(shingle_doc,k=2),wos_docs_i)
    pool.terminate()
    
    
    

if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")

