from django.core.management.base import BaseCommand, CommandError
from tmv_app.views import *
from tmv_app.models import *
import pandas as pd

class Command(BaseCommand):
    help = 'update a run, do a load of calculations  \
    on it so that it loads quicker'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)

    def handle(self, *args, **options):
        run_id = options['run_id']
        allys = True
        if allys:
            print(run_id)

            dts = DocTopic.objects.filter(run_id=run_id)

            df = pd.DataFrame(list(dts.values('doc_id','topic_id','scaled_score')))

            df = df.pivot(index='doc_id',columns='topic_id',values='scaled_score').fillna(0)
            #df = df.pivot(index='topic_id',columns='doc_id',values='scaled_score')

            # pseudo code for docwise:
            # There are 96 billion combinations, so need to limit
            # For each doc, compare with docs that have a topic_score > 0 of the
            # Largest topic in the doc.
            ar = -1

            corr = df.corr()
            values = corr.values
            cols = corr.columns

            TopicCorr.objects.filter(run_id=run_id,ar=ar).delete()

            for c in range(len(cols)):
                topic = cols[c]
                tcor = values[c]
                for tc in range(len(tcor)):
                    corrtopic = cols[tc]
                    corrscore = tcor[tc]
                    if corrscore > 0:
                        topiccorr, created = TopicCorr.objects.get_or_create(
                            topic_id=topic, topiccorr_id=corrtopic, run_id=run_id,
                            ar=ar
                        )
                        topiccorr.score = corrscore
                        topiccorr.save()

        ars = [
            {"name":"AR0","years":range(0,1985),"n":0},
            {"name":"AR1","years":range(1985,1991),"n":1},
            {"name":"AR2","years":range(1991,1995),"n":2},
            {"name":"AR3","years":range(1995,2001),"n":3},
            {"name":"AR4","years":range(2001,2008),"n":4},
            {"name":"AR5","years":range(2008,2014),"n":5},
            {"name":"AR6","years":range(2014,9999),"n":6}
        ]
        for ar in ars:
            print(ar)
            a = ar['name']
            ys = ar['years']
            ytopics = DocTopic.objects.filter(run_id=run_id,doc__PY__in=ys)
            if ytopics.count() == 0:
                continue
            TopicCorr.objects.filter(run_id=run_id,ar=ar['n']).delete()

            df = pd.DataFrame(list(ytopics.values('doc_id','topic_id','scaled_score')))
            df = df.pivot(index='doc_id',columns='topic_id',values='scaled_score').fillna(0)

            corr = df.corr()
            values = corr.values
            cols = corr.columns



            for c in range(len(cols)):
                topic = cols[c]
                tcor = values[c]
                for tc in range(len(tcor)):
                    corrtopic = cols[tc]
                    corrscore = tcor[tc]
                    if corrscore > 0:
                        topiccorr, created = TopicCorr.objects.get_or_create(
                            topic_id=topic, topiccorr_id=corrtopic, run_id=run_id,
                            ar=ar['n']
                        )
                        topiccorr.score = corrscore
                        topiccorr.save()
