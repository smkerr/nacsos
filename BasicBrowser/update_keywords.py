import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import csv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *
import tmv_app.models as tm

owtable = {}

with open('OECDWoS.csv') as infile:
    reader = csv.reader(infile,delimiter='\t')
    for row in reader:
        owtable[row[2]] = {"OECD": row[3],"OECD_FOS":row[0],"OECD_FOS_TEXT":row[1]}

docs = Doc.objects.filter(
    wosarticle__wc__isnull=False,query=1457,
    wc__isnull=True
)

print(docs.count())

aut = list(Doc.objects.filter(UT__contains='WOS:').values_list('UT',flat=True))

for d in docs:
    for k in d.wosarticle.wc:
        kws = k.split(";")
        for kw in kws:
            kw = kw.strip()
            try:
                okw = owtable[kw.upper()]
            except:
                print(repr(kw.upper()))
                continue
            dkw, created = WC.objects.get_or_create(text=kw.strip())
            if created:
                dkw.oecd=okw["OECD"]
                dkw.oecd_fos = okw["OECD_FOS"]
                dkw.oecd_fos_text = okw["OECD_FOS_TEXT"]
                dkw.save()
            dkw.doc.add(d)
            break
