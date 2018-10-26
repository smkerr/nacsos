from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

import re, nltk
from nltk.stem import SnowballStemmer

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('--qid',type=int, default=0)

    def handle(self, *args, **options):
        qid = options['qid']
        if qid==0:
            docs = Doc.objects.all()
            print(docs.count())
        else:
            q = Query.objects.get(pk=qid)
            docs = Doc.objects.filter(
                query=q
            )
            print(docs.count())

        docs = Doc.objects.filter(
            kw__isnull=True,
            wosarticle__isnull=False
        )

        print(docs.count())

        for d in docs.iterator():
            if d.wosarticle.de is not None:
                for kw in d.wosarticle.de.split(';'):
                    t = kw.strip().lower()
                    if len(t) < 50:
                        kwobj, created = KW.objects.get_or_create(
                            text=t,
                            kwtype=0
                        )
                        kwobj.doc.add(d)
            if d.wosarticle.kwp is not None:
                for kw in d.wosarticle.kwp.split(';'):
                    t = kw.strip().lower()
                    if len(t) < 50:
                        kwobj, created = KW.objects.get_or_create(
                            text=t,
                            kwtype=1
                        )
                        kwobj.doc.add(d)
