from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from tmv_app.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer
from time import time

from utils.utils import *# flatten

class Command(BaseCommand):
    help = 'do open heart surgery on database'

    def handle(self, *args, **options):

        def get_objs(objs, test):
            n = objs.count()
            if n > 100000:
                p = n*0.00001
            else:
                p = n*0.1

            #p = 100
            if test:
                try:
                    objs = objs[:p]
                except:
                    objs = objs
            return(objs)

        test = False

        def copy_docs(doc):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=doc.UT
            )
            for q in doc.query.all():
                dc.query.add(q)
            for t in doc.tag.all():
                dc.tag.add(t)
            dc.title = doc.title
            dc.tilength=doc.tilength
            dc.content = doc.content
            dc.PY = doc.PY
            dc.first_author = doc.first_author
            dc.authors = doc.authors
            for t in doc.technology.all():
                dc.technology.add(t)
            for i in doc.innovation.all():
                dc.innovation.add(i)
            for c in doc.category.all():
                dc.category.add(c)
            dc.source = doc.source
            dc.wos = doc.wos
            dc.scopus = doc.scopus
            dc.uploader = doc.uploader
            dc.date = doc.date
            dc.ymentions = doc.ymentions
            for c in doc.cities.all():
                dc.cities.add(c)
            dc.citation_objects = doc.citation_objects
            dc.duplicated = doc.duplicated
            dc.relevant = doc.relevant

            dc.save()

        print("Processing docs")
        objs = Doc.objects.all()
        if test:
            try:
                objs = objs[:20]
            except:
                objs = objs
        t0 = time()
        pool = Pool(processes=6)
        pool.map(copy_docs,objs)
        pool.terminate()
        gc.collect()
        django.db.connections.close_all()
        print("done in %0.3fs." % (time() - t0))

        #  <ManyToOneRel: scoping.networkproperties>,
        # 88683
