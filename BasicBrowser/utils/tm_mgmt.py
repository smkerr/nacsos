from tmv_app.models import *
from scoping.models import *
from tmv_app.tasks import *
from celery import *
from django.db.models import Q, Count, Func, F, Sum, Avg, Value as V
from celery import group
import pandas as pd

def compare_topic_queryset(runs):

    stat = runs.first()
    if stat.method == "DT":
        dynamic = True
    else:
        dynamic = False

    col1s = []
    col2s = []
    ss = []
    scols = []

    runs = runs.order_by('K').values_list('run_id',flat=True)

    for i in range(1,len(runs)):
        if dynamic==True:
            topics1 = DynamicTopic.objects.filter(run_id=runs[i-1])
            topics2 = DynamicTopic.objects.filter(run_id=runs[i])
        else:
            topics1 = Topic.objects.filter(run_id=runs[i-1])
            topics2 = Topic.objects.filter(run_id=runs[i])


        df = pd.DataFrame.from_dict(list(topics2.values('title','score')))
        df2 = pd.DataFrame.from_dict([{'title': 'None','score': 0}])
        df = df.append(df2)
        col1 = "run_{}_topics_{}".format(runs[i-1],topics1.count())
        scol = "scores_{}".format(runs[i])
        bscol = "scores_{}".format(runs[i-1])

        if i==1:
            scols.append(bscol)

        col1s.append(col1)
        scols.append(scol)

        col2 = "run_{}_topics_{}".format(runs[i], topics2.count())

        col2s.append(col2)

        s = "similarity_{}-{}".format(runs[i-1],runs[i])
        ss.append(s)

        df = df.rename(columns = {'title': col2, 'score': scol})

        df[s] = 0
        df[col1] = "None"
        df[bscol] = 0

        for t in topics2:
            scores = [0]
            titles = [""]
            tscores = [0]
            for ct in topics1:
                score = len(set(t.top_words).intersection(set(ct.top_words)))
                if score>0:
                    scores.append(score)
                    titles.append(ct.title)
                    tscores.append(ct.score)


            m = max(scores)
            df.loc[df[col2]==t.title, s] = m
            if m==0:
                df.loc[df[col2]==t.title, col1] = 'None'
            else:
                df.loc[df[col2]==t.title, col1] = titles[scores.index(max(scores))]
                df.loc[df[col2]==t.title, bscol] = tscores[scores.index(max(scores))]


        if i==1:
            #df = pd.DataFrame.from_dict(list(topics2.values('title')))
            mdf = df
        else:
            mdf = mdf.merge(df,how="outer").fillna("")


    columns = []
    for i in range(len(col1s)):
        columns.append(col1s[i])
        columns.append(scols[i])
        columns.append(ss[i])
        if i == len(col1s)-1:
            columns.append(col2s[i])
            columns.append(scols[i+1])

    print(columns)

    mdf = mdf[columns]


    res = mdf.groupby(columns)
    res = res.apply(lambda x: x.sort_values(s,ascending=False))

    l = len(res)

    return [res,ss]

    # fname = "/tmp/run_compare_{}_{}.xlsx".format(runs[0],runs[len(runs)-1])
    #
    # writer = pd.ExcelWriter(fname, engine='xlsxwriter')
    #
    # res.to_excel(writer)
    #
    # worksheet = writer.sheets['Sheet1']
    #
    # for i in range(len(ss)):
    #     if (i+1)*3 > 26:
    #         c = 'A'+chr(ord('A')-1+((i+1)*3)-26)
    #     else:
    #         c = chr(ord('A')-1+(i+1)*3)
    #     r = "{}2:{}{}".format(c,c,len(res))
    #     print(r)
    #
    #     worksheet.conditional_format(r, {
    #         'type': '3_color_scale',
    #         'min_value': 0,
    #         'mid_value': 5,
    #         'max_value': 10,
    #         'min_type': 'num',
    #         'mid_type': 'num',
    #         'max_type': 'num',
    #     })
    #
    # writer.save()


def update_topic_titles(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)

    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_titles_current:
    #if "a" in "ab":
        for topic in Topic.objects.filter(run_id=run_id):
            #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')[:3]
            topicterms = Term.objects.filter(topicterm__topic=topic).order_by('-topicterm__score')[:10]
            new_topic_title = '{'
            for tt in topicterms[:3]:
                new_topic_title +=tt.title
                new_topic_title +=', '
            new_topic_title = new_topic_title[:-2]
            new_topic_title+='}'


            topic.top_words = [x.title.lower() for x in topicterms]

            topic.title = new_topic_title
            topic.save()
        stats.topic_titles_current = True
        stats.save()



def update_bdtopics(run_id):
    stats = RunStats.objects.get(pk=run_id)
    if "a"=="a":
    #if not stats.topic_titles_current:
        topics = Topic.objects.filter(run_id=run_id)
        for topic in topics:
            tts = TopicTerm.objects.filter(topic=topic)
            at = tts.values('term').annotate(
                mean = models.Avg('score')
            ).order_by('-mean')[:3]
            new_topic_title = '{'
            for tt in at:
                term = Term.objects.get(pk=tt['term'])
                new_topic_title += term.title
                new_topic_title +=', '
            new_topic_title = new_topic_title[:-2]
            new_topic_title+='}'
            topic.title = new_topic_title
            topic.save()

def update_dtopics(run_id):
    stats = RunStats.objects.get(pk=run_id)
    if stats.parent_run_id is not None:
        parent_run_id=stats.parent_run_id
    else:
        parent_run_id = run_id
    #if "a" == "b":
    if not stats.topic_titles_current:
        doc_ids = set(list(DocTopic.objects.filter(
            run_id=parent_run_id
        ).values_list('doc_id',flat=True)))
        # for tp in stats.periods.all():
        #     y_ids = list(Doc.objects.filter(
        #         pk__in=doc_ids,
        #         PY__in=tp.ys
        #     ).values_list('id',flat=True))
        #
        #     ds = DocTopic.objects.filter(
        #         doc__id__in=y_ids,
        #         run_id=parent_run_id
        #     ).aggregate(
        #         tscore = Sum('score')
        #     )['tscore']
        #     tdt, created = TimeDocTotal.objects.get_or_create(
        #         period=tp,
        #         run=stats
        #     )
        #     tdt.n_docs = len(y_ids)
        #     tdt.dt_score = ds
        #     tdt.save()
        #     wts = Topic.objects.filter(
        #         run_id=stats.parent_run_id,
        #         year = tp.n
        #     )
        #     for wt in wts:
        #         wt.period = tp
        #         wt.save()

    #if "a" in "ab":
        dts = DynamicTopic.objects.filter(
            run_id=run_id
        ).values_list('id',flat=True)
        jobs = group(update_dtopic.s(dt,parent_run_id) for dt in dts)
        result = jobs.apply_async()
        stats.topic_titles_current = True
        stats.save()

    return

def update_topic_titles_hlda(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)

    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_titles_current:
    #if "a" in "ab":
        for topic in HTopic.objects.filter(run_id=run_id):
            #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')[:3]
            topicterms = Term.objects.filter(htopicterm__topic=topic.topic).order_by('-htopicterm__count')[:3]
            new_topic_title = '{'
            for tt in topicterms:
                new_topic_title +=tt.title
                new_topic_title +=', '
            new_topic_title = new_topic_title[:-2]
            new_topic_title+='}'

            topic.title = new_topic_title
            topic.save()
        stats.topic_titles_current = True
        stats.save()


def update_topic_scores(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)
    stats = RunStats.objects.get(run_id=run_id)
    #if "a" in "ab":
    if not stats.topic_scores_current:

        topics = Topic.objects.filter(run_id=stats)
        for t in topics:
            t.score=0
            t.save()

        topics = DocTopic.objects.filter(run_id=run_id).values('topic').annotate(
            total=Sum('score')
        )
        for tscore in topics:
            topic = Topic.objects.get(pk=tscore['topic'])
            topic.score = tscore['total']
            topic.save()



        stats.topic_scores_current = True
        stats.save()

# class TopicARScores(models.Model):
#     topic = models.ForeignKey('Topic',null=True)
#     ar = models.ForeignKey('scoping.AR',null=True)
#     score = models.FloatField(null=True)
#     share = models.FloatField(null=True)
#     pgrowth = models.FloatField(null=True)
#     pgrowthn = models.FloatField(null=True)


def update_ar_scores(run_id):
    stat = RunStats.objects.get(pk=run_id)
    for ar in AR.objects.all().order_by('ar'):
        years = list(range(ar.start,ar.end))
        ytopics = DocTopic.objects.filter(
            doc__PY__in=years,
            run_id=run_id,
            score__gt=stat.dthreshold
        ).values('topic_id').annotate(
            ttotal=models.Sum('score')
        )
        atotal = ytopics.aggregate(
            s=models.Sum('ttotal')
        )['s']
        for yt in ytopics:
            ars, created = TopicARScores.objects.get_or_create(
                topic_id=yt['topic_id'],
                ar=ar
            )
            ars.score = yt['ttotal']
            ars.share = ars.score / atotal
            if ar.ar>0:
                par, created = TopicARScores.objects.get_or_create(
                    topic_id=yt['topic_id'],
                    ar__ar=ar.ar-1
                )
                if created:
                    par.score = 0
                    par.pgrowth = 0
                    par.save()
                if par.score == 0:
                    ars.pgrowth=100
                else:
                    ars.pgrowth = (ars.score - par.score) / par.score * 100
            ars.save()

    run_ars = TopicARScores.objects.filter(
        topic__run_id=run_id,
        ar__ar__gt=0
    )

    ar_av = run_ars.values('ar').annotate(
        av_growth = Avg('pgrowth')
    )

    for ar in ar_av:
        ars = run_ars.filter(ar=ar['ar'])
        n = abs(ar['av_growth'])
        ars.update(
            pgrowthn = F('pgrowth') / n
        )

def update_ipcc_coverage(run_id):
    runstat = RunStats.objects.get(pk=run_id)
    dts = DocTopic.objects.filter(
        run_id=run_id,
        doc__PY__lt=2014,
        score__gt=runstat.dthreshold
    ).values('topic_id')

    dts = dts.annotate(
        ipcc = models.Sum(
            models.Case(
                models.When(doc__ipccref__isnull=False,then=F('score')),default=0, output_field=models.FloatField()
            )
        ),
        no_ipcc = models.Sum(
            models.Case(
                models.When(doc__ipccref__isnull=True,then=F('score')),default=0, output_field=models.FloatField()
            )
        )
    )
    for dt in dts:
        t = Topic.objects.get(pk=dt['topic_id'])
        t.ipcc_coverage = dt['ipcc'] / (dt['ipcc'] + dt['no_ipcc'])
        t.save()

def update_primary_topic(run_id):
    return None
    runstat = RunStats.objects.get(pk=run_id)
    docs = Doc.objects.filter(query=runstat.query)
    docs = docs.filter(ipccref__isnull=False)
    for d in docs.iterator():
        t = Topic.objects.filter(doctopic__doc=d,run_id=run_id).order_by('-doctopic__score').first()
        if t is not None:
            d.primary_topic.add(t)

def update_year_topic_scores(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)
    stats = RunStats.objects.get(run_id=run_id)
    #if "a" in "a":
    if not stats.topic_year_scores_current:
        if stats.get_method_display() == 'hlda':
            yts = HDocTopic.objects.filter(doc__PY__gt=1989,run_id=run_id)

            yts = yts.values('doc__PY').annotate(
                yeartotal=Count('doc')
            )

            ytts = yts.values().values('topic','topic__title','doc__PY').annotate(
                score=Count('doc')
            )
            HTopicYear.objects.filter(run_id=run_id).delete()
            for ytt in ytts:
                yttyear = ytt['doc__PY']
                topic = HTopic.objects.get(topic=ytt['topic'])
                for yt in yts:
                    ytyear = yt['doc__PY']
                    if yttyear==ytyear:
                        yeartotal = yt['yeartotal']
                try:
                    topicyear = HTopicYear.objects.get(topic=topic,PY=yttyear, run_id=run_id)
                except:
                    topicyear = HTopicYear(topic=topic,PY=yttyear,run_id=run_id)
                topicyear.score = ytt['score']
                topicyear.count = yeartotal
                topicyear.save()
        else:
            yts = DocTopic.objects.filter(doc__PY__gt=1989,run_id=run_id)

            yts = yts.values('doc__PY').annotate(
                yeartotal=Sum('scaled_score')
            )

            ytts = yts.values().values('topic','topic__title','doc__PY').annotate(
                score=Sum('scaled_score')
            )
            TopicYear.objects.filter(run_id=run_id).delete()
            for ytt in ytts:
                yttyear = ytt['doc__PY']
                topic = Topic.objects.get(pk=ytt['topic'])
                for yt in yts:
                    ytyear = yt['doc__PY']
                    if yttyear==ytyear:
                        yeartotal = yt['yeartotal']

                topicyear, created = TopicYear.objects.get_or_create(
                    topic=topic,PY=yttyear, run_id=run_id
                )
                topicyear.score = ytt['score']
                topicyear.count = yeartotal
                topicyear.save()



        stats.topic_year_scores_current = True
        stats.save()
