from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from tmv_app.models import *
from tmv_app.tasks import *
import os, time

import re, nltk
from nltk.stem import SnowballStemmer

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('-r',type=int, required = True)
        parser.add_argument('-l','--list', nargs='+', help='<Required> list', required=True)

    def handle(self, *args, **options):
        run_id = options['r']
        Ks = options['list']
        stat = RunStats.objects.get(pk=run_id)
        for K in Ks:
            K = int(K)
            print(K)
            s = RunStats(
                max_features=stat.max_features,
                min_freq=stat.min_freq,
                max_df=stat.max_df,
                limit=stat.limit,
                ngram=stat.ngram,
                db=False,
                K=K,
                alpha=stat.alpha,
                max_iter=stat.max_iter,
                query=stat.query,
                method=stat.method
            )
            s.save()

            wait=True
            while wait==True:
                if os.getloadavg()[0] > 5:
                    time.sleep(60)
                else:
                    wait = False
            do_nmf.delay(s.run_id)

            time.sleep(180)
