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
    wosarticle__wc__isnull=False,
    wc__isnull=True
)

print(docs.count())

aut = list(Doc.objects.filter(UT__UT__contains='WOS:').values_list('UT',flat=True))

broken_1s = ["EDUCATION & EDUCATIONAL","HOSPITALITY, LEISURE, SPORT &"]
broken_2s = ["RESEARCH","TOURISM"]

for d in docs:
    print(d.wosarticle.wc)
    kw_list = []
    kws = list(flatten([x.split(";") for x in d.wosarticle.wc]))
    for j,kw in enumerate(kws):
        # Get the last or next keyword, or set to None
        if j > 0:
            lkw = kws[j-1].strip().upper()
        else:
            lkw = None
        if j < len(kws)-1:
            nkw = kws[j+1].strip().upper()
        else:
            nkw = None

        kw = kw.strip().upper()
        if kw=="":
            continue
        elif kw in broken_1s and nkw in broken_2s:
            kw_list.append(f"{kw} {nkw}")
        elif kw in broken_2s and lkw in broken_1s:
            continue
        else:
            kw_list.append(kw)
    d.wosarticle.wc = kw_list
    d.wosarticle.save()


for d in docs:
    for k in d.wosarticle.wc:
        kws = k.split(";")
        for kw in kws:
            kw = kw.strip()
            if kw=="":
                continue
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
            #break
