import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import csv
from urllib.parse import urlparse, parse_qsl

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

docs = Doc.objects.all()

for d in docs:
    das = d.docauthinst_set.order_by('AU','position').distinct('AU').values_list('id',flat=True)
    unique = d.docauthinst_set.filter(id__in=das).order_by('position').values_list('AU',flat=True)
    d.authors = ", ".join(unique)
    fa = d.docauthinst_set.order_by('position').first()
    if fa is not None:
        d.first_author = fa.AU
    d.save()
