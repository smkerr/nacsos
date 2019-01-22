from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer

from utils.utils import *# flatten
from scoping.models import *

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)

    def handle(self, *args, **options):
        qid = options['qid']

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
        chunk_size = 1000

        for i in range(ndocs//chunk_size+1):
            cdos = []
            f = i*chunk_size
            print(f)
            l = (i+1)*chunk_size
            if l > ndocs:
                l = ndocs-1
            chunk_docs = docs[f:l]
            pool = Pool(processes=4)
            cdos.append(pool.map(doc_cites,chunk_docs))
            pool.terminate()
            gc.collect()


            django.db.connections.close_all()
            cdos = flatten(cdos)

            CDO.objects.bulk_create(cdos)
