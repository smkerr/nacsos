from django.core.management.base import BaseCommand, CommandError
from tmv_app.views import *
from tmv_app.models import *
from parliament.models import *
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

        def correlate_topics(df,period,obj):


            df = df.pivot(
                index=doc_id,
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
                        # for backward compatibility
                        if type(period) is dict:
                            topiccorr, created = obj.objects.get_or_create(
                                topic_id=topic, topiccorr_id=corrtopic, run_id=run_id,
                                ar=period['n']
                            )
                        else:
                            topiccorr, created = obj.objects.get_or_create(
                                topic_id=topic, topiccorr_id=corrtopic, run_id=run_id,
                                period=period
                            )
                        topiccorr.score = corrscore
                        topiccorr.save()

        run_id = options['run_id']
        allys = True
        if allys:
            print(run_id)
            stat = RunStats.objects.get(pk=run_id)

            if stat.psearch is not None:
                doc_id = 'ut_id'
                tars = DynamicTopicTimePeriodScores
            else:
                doc_id = 'doc_id'
                tars = DynamicTopicARScores

            if stat.method=="DT":
                periods = stat.periods.all()
                dts = DocTopic.objects.filter(
                    topic__topicdtopic__dynamictopic__run_id=run_id,
                    topic__topicdtopic__score__gt=0.05,
                    score__gt=0.05
                ).values(
                    doc_id,'topic__topicdtopic__dynamictopic_id'
                ).annotate(
                    tc=Sum(F('score') * F('topic__topicdtopic__score'),
                )).values(
                    doc_id,
                    'topic__topicdtopic__dynamictopic_id',
                    'tc'
                )

                df = dfdt(list(dts))

                obj = DynamicTopicCorr

            else:
                periods = scoping.models.AR.objects.all()
                dts = DocTopic.objects.filter(run_id=run_id).values(
                    doc_id,'topic_id','score'
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


        for period in periods:  # can be period or ar object
            if hasattr(period,'name'):
                a = period.name
                ys = range(period.start, period.end + 1)
                period.n = period.ar
            else:
                a = period.title

            if stat.query:
                ytopics = dts.filter(doc__PY__in=ys)
            elif stat.psearch:
                if period.start_date:
                    ytopics = dts.filter(ut__document__date__gte=period.start_date,
                                         ut__document__date__lte=period.end_date)
                elif period.ys:
                    ys = period.ys
                    #ytopics = dts.filter(ut__document__date__year__in=ys)
                    ytopics = dts.filter(ut__document__parlperiod__n__in=ys)
                else:
                    print("No information for determining time period")
                    return 1

                # print(ytopics)

            else:
                print("Error: Did not find query or psearch")
                return 1

            if ytopics.count() == 0:
                print("No topics in period!")
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
                if stat.psearch:
                    tar, created = tars.objects.get_or_create(
                        period_id=period.id,
                        topic_id=ts['tid']
                    )
                else:
                    tar, created = tars.objects.get_or_create(
                        ar_id=period.id,
                        topic_id=ts['tid']
                    )
                tar.score = ts['ts']
                tar.save()

            if isinstance(period, scoping.models.AR):
                obj.objects.filter(run_id=run_id, ar=period.ar).delete()
            elif isinstance(period, TimePeriod):
                obj.objects.filter(run_id=run_id, period=period.n).delete()

            df = dfdt(list(ytopics))

            correlate_topics(df,period,obj)
