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

        def dfdt(qs):
            ## Make a queryset of doctopics into a pandas
            ## df in the format we want to used
            df = pd.DataFrame(qs)
            if 'topic_id' not in df.columns:
                df = df.rename(columns={
                    'tc': 'score',
                    'topic__topicdtopic__dynamictopic_id': 'topic_id'
                })
            return df

        def correlate_topics(df,ar,obj):

            df = df.pivot(
                index='doc_id',
                columns='topic_id',
                values='score'
            ).fillna(0)

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
                        topiccorr, created = obj.objects.get_or_create(
                            topic_id=topic, topiccorr_id=corrtopic, run_id=run_id,
                            ar=ar['n']
                        )
                        topiccorr.score = corrscore
                        topiccorr.save()

        run_id = options['run_id']
        allys = True
        if allys:
            print(run_id)
            stat = RunStats.objects.get(pk=run_id)

            if stat.method=="DT":
                dts = DocTopic.objects.filter(
                    topic__topicdtopic__dynamictopic__run_id=run_id,
                    topic__topicdtopic__score__gt=0.05,
                    score__gt=0.05
                ).values(
                    'doc_id','topic__topicdtopic__dynamictopic_id'
                ).annotate(
                    tc=Sum(F('score') * F('topic__topicdtopic__score'),
                )).values(
                    'doc_id',
                    'topic__topicdtopic__dynamictopic_id',
                    'tc'
                )

                df = dfdt(list(dts))


                obj = DynamicTopicCorr
                tars = DynamicTopicARScores

            else:
                dts = DocTopic.objects.filter(run_id=run_id).values(
                    'doc_id','topic_id','score'
                )
                df = dfdt(list(dts))

                tars = TopicARScores
                obj = TopicCorr

            #df = df.pivot(index='topic_id',columns='doc_id',values='scaled_score')

            # pseudo code for docwise:
            # There are 96 billion combinations, so need to limit
            # For each doc, compare with docs that have a topic_score > 0 of the
            # Largest topic in the doc.
            ar = {'n':-1}
            obj.objects.filter(run_id=run_id,ar=ar['n']).delete()
            correlate_topics(df,ar,obj)

        ars = scoping.models.AR.objects.all().values()
        for ar in ars:
            print(ar)
            a = ar['name']
            ar['n'] = ar['ar']
            ys = range(ar['start'],ar['end']+1)
            ytopics = dts.filter(doc__PY__in=ys)
            if ytopics.count() == 0:
                continue

            if stat.method=="DT":
                tscores = ytopics.values(
                    'topic__topicdtopic__dynamictopic_id'
                ).annotate(
                    ts = Sum(F('score')*F('topic__topicdtopic__score')),
                    tid = F('topic__topicdtopic__dynamictopic_id')
                )
            else:
                tscores = ytopics.values(
                    'topic_id'
                ).annotate(
                    ts = Sum('score'),
                    tid = F('topic_id')
                )


            for ts in tscores:
                tar, created = tars.objects.get_or_create(
                    ar_id=ar['id'],
                    topic_id=ts['tid']
                )
                tar.score = ts['ts']
                tar.save()

            obj.objects.filter(run_id=run_id,ar=ar['ar']).delete()

            df = dfdt(list(ytopics))

            correlate_topics(df,ar,obj)
