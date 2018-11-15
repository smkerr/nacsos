from tmv_app.models import *
from scoping.models import *
from tmv_app.tasks import *
from parliament.models import Paragraph, Utterance

from celery import *
from django.db.models import Q, Count, Func, F, Sum, Avg, Subquery, OuterRef, Value as V
from celery import group
import pandas as pd
from multiprocess import Pool


def compare_topic_queryset(runs):

    col1s = []
    col2s = []
    ss = []
    scols = []

    stat = runs.first()

    if runs.count() == 1 and runs.first().method=="DT":
        windows = True
        runs = stat.periods.all().order_by('n')
    else:
        windows = False
        runs = runs.order_by('K').values_list('run_id',flat=True)

    for i in range(1,len(runs)):

        if windows:
            s1 = runs[i-1]
            s2 = runs[i]
            topics1 = Topic.objects.filter(run_id=stat.parent_run_id,period=s1)
            topics2 = Topic.objects.filter(run_id=stat.parent_run_id,period=s2)

        else:
            s1 = RunStats.objects.get(pk=runs[i-1])
            s2 = RunStats.objects.get(pk=runs[i])

            if s1.method=="DT":
                topics1 = DynamicTopic.objects.filter(run_id=runs[i-1])
            else:
                topics1 = Topic.objects.filter(run_id=runs[i-1])

            if s2.method=="DT":
                topics2 = DynamicTopic.objects.filter(run_id=runs[i])
            else:
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

        df[scol] = df[scol].astype(object)

        df[s] = 0
        df[col1] = "None"
        df[bscol] = 0
        df[bscol] = df[bscol].astype(object)

        for t in topics2:
            scores = [0]
            titles = [""]
            tscores = [0]
            for ct in topics1:
                # compare overlap between top words
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

        for c in df.columns:
            df[c] = df[c].astype(object)

        if i==1:
            #df = pd.DataFrame.from_dict(list(topics2.values('title')))
            mdf = df
        else:
            for c in mdf.columns:
                mdf[c] = mdf[c].astype(object)
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

def yearly_topic_term_scores(run_id):

    stat=RunStats.objects.get(pk=run_id)
    if stat.parent_run_id is not None:
        parent_run_id = stat.parent_run_id
    else:
        parent_run_id = run_id

    ytds = DocTopic.objects.filter(
        run_id=parent_run_id
    ).values('topic__year').annotate(
        dtopic_score = F('score') * F('topic__topicdtopic__score')
    ).annotate(
        yscore = Sum('dtopic_score')
    )

    dt_ids = DynamicTopic.objects.filter(
        run_id=run_id#,
        #dynamictopicyear__isnull=True
    ).values_list('id',flat=True)

    jobs = group(yearly_topic_term.s(dt,run_id) for dt in dt_ids)
    result = jobs.apply_async()

def update_dtopics(run_id):
    stats = RunStats.objects.get(pk=run_id)
    if stats.parent_run_id is not None:
        parent_run_id=stats.parent_run_id
    else:
        parent_run_id = run_id
    #if "a" == "b":
    if not stats.topic_titles_current:

        ##### DocTopics

        if stats.query:
            doc_ids = set(list(DocTopic.objects.filter(
                run_id=parent_run_id
            ).values_list('doc_id',flat=True)))
        elif stats.psearch.search_object_type == 1:
            doc_ids = set(list(DocTopic.objects.filter(
                run_id=parent_run_id
            ).values_list('par_id',flat=True)))
        elif stats.psearch.search_object_type == 2:
            doc_ids = set(list(DocTopic.objects.filter(
                run_id=parent_run_id
            ).values_list('par_id', flat=True)))
        else:
            print("Document id could not be identified")

        if stats.periods.count() == 0:
            ys = RunStats.objects.get(
                pk=parent_run_id
            ).topic_set.distinct(
                'year'
            ).order_by('year').values_list('year',flat=True)
            for i,y in enumerate(ys):
                tp, created = TimePeriod.objects.get_or_create(
                    title=str(y),
                    n = i,
                    ys = [y]
                )
                stats.periods.add(tp)


        for tp in stats.periods.all():
            if len(tp.ys)==1:
                wts = Topic.objects.filter(
                    run_id=stats.parent_run_id,
                    year = tp.ys[0]
                )
            else:
                wts = Topic.objects.filter(
                    run_id=stats.parent_run_id,
                    year = tp.n
                )

            for wt in wts:
                wt.period = tp
                wt.save()

            ds = TopicDTopic.objects.filter(
                dynamictopic__run_id=run_id,
                topic__in=wts
            ).annotate(
                dtopic_score = F('score') * F('topic__score')
            ).aggregate(
                t=Sum('dtopic_score')
            )['t']


            tdt, created = TimeDocTotal.objects.get_or_create(
                period=tp,
                run=stats
            )

            if stats.query:
                tdt.n_docs = Doc.objects.filter(
                    pk__in=doc_ids,
                    PY__in=tp.ys
                    ).count()
            elif stats.psearch.search_object_type == 1:
                tdt.n_docs = Paragraph.objects.filter(
                    pk__in=doc_ids,
                    utterance__document__date__year__in=tp.ys
                    ).count()
            elif stats.psearch.search_object_type == 2:
                tdt.n_docs = Utterance.objects.filter(
                    pk__in=doc_ids,
                    document__date__year__in=tp.ys
                    ).count()

            tdt.dt_score = ds
            tdt.save()


    #if "a" in "ab":
        dts = DynamicTopic.objects.filter(
            run_id=run_id
        ).values_list('id',flat=True)

        #pool = Pool(processes=8)
        #pool.map(partial(update_dtopic, parent_run_id=parent_run_id), dts)
        #pool.terminate()
        for dt in dts:
            update_dtopic(dt, parent_run_id)

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

def calculate_topic_scores(topics):
    top_total = topics.aggregate(t=Sum('doctopic__score'))['t']
    topics = topics.annotate(
        sum_score=Sum('doctopic__score')
    )
    for t in topics:
        t.score = t.sum_score
        if t.score is None:
            t.score=0
        t.share = t.score/top_total
        t.save()

def update_topic_scores(run_id):
    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_scores_current:
        if stats.method=="DT":
            for p in stats.periods.all():
                topics = Topic.objects.filter(
                    run_id=stats,period=p
                )
                calculate_topic_scores(topics)
        else:
            topics = Topic.objects.filter(run_id=stats)
            calculate_topic_scores(topics)
        stats.topic_scores_current = True
        stats.save()

def update_ar_scores(run_id):
    stat = RunStats.objects.get(pk=run_id)
    for ar in AR.objects.all().order_by('ar'):
        years = list(range(ar.start,ar.end))
        ytopics = DocTopic.objects.filter(
            doc__PY__in=years,
            run_id=run_id,
            score__gt=stat.dt_threshold
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

def normalise_tdts(run_id):
    stat = RunStats.objects.get(pk=run_id)
    tdts = TimeDTopic.objects.filter(
        dtopic__run_id=run_id
    )
    tdts_av = tdts.values('period').annotate(
        av_growth = Avg('pgrowth')
    )
    for tp in tdts_av:
        tptdts = tdts.filter(period=tp['period'])
        try:
            n = abs(tp['av_growth'])
            tptdts.update(
                pgrowthn = F('pgrowth') / n
            )
        except:
            tptdts.update(
                pgrowthn=0
            )



def update_ipcc_coverage(run_id):

    wgs = [
        {"WG":1, "score": 0},
        {"WG":2, "score": 0},
        {"WG":3, "score": 0}
    ]

    def ipcc_annotate_dts(dts,run_id,tp=None):
        dts = dts.annotate(
            ipcc = models.Sum(
                models.Case(
                    models.When(
                        doc__ipccref__isnull=False,
                        then=F('score')*F('topic__topicdtopic__score')
                    ),
                    default=0,
                    output_field=models.FloatField()
                )
            ),
            no_ipcc = models.Sum(
                models.Case(
                    models.When(
                        doc__ipccref__isnull=True,
                        then=F('score')*F('topic__topicdtopic__score')
                    ),
                    default=0,
                    output_field=models.FloatField()
                )
            )
        )
        for dt in dts:
            t = DynamicTopic.objects.get(
                pk=dt['topic__topicdtopic__dynamictopic__id']
            )
            if tp:
                tdt, created = TimeDTopic.objects.get_or_create(
                    dtopic=t,
                    period=tp
                )
                tdt.ipcc_score = dt['ipcc']
                tdt.ipcc_coverage = dt['ipcc'] / (dt['ipcc'] + dt['no_ipcc'])
                tdt.save()

            else:

                t.ipcc_score = dt['ipcc']
                t.ipcc_time_score = dt['ipcc'] + dt['no_ipcc']
                t.ipcc_coverage = dt['ipcc'] / (dt['ipcc'] + dt['no_ipcc'])
                t.save()

        if tp:
            topics = TimeDTopic.objects.filter(
                dtopic__run_id=run_id,
                period=tp
            )
            tsums = topics.aggregate(
                ip_score=Sum('ipcc_score'),
                score=Sum('score')
            )

            topics.update(
                ipcc_share=F('ipcc_score')/tsums['ip_score'],
                share=F('score')/tsums['score']
            )
        else:
            topics = DynamicTopic.objects.filter(
                run_id=run_id
            )
            tsums = topics.aggregate(
                ip_score=Sum('ipcc_score'),
                score=Sum('ipcc_time_score')
            )

            topics.update(
                ipcc_share=F('ipcc_score')/tsums['ip_score'],
                share=F('ipcc_time_score')/tsums['score']
            )

        return

    runstat = RunStats.objects.get(pk=run_id)

    if runstat.method=="DT":
        dts = DocTopic.objects.filter(
            run_id=run_id,
            doc__PY__lt=2014,
            score__gt=runstat.dt_threshold,
            topic__topicdtopic__dynamictopic__run_id=run_id,
            topic__topicdtopic__score__gt=runstat.dt_threshold
        ).values('topic__topicdtopic__dynamictopic__id')

        ipcc_annotate_dts(dts, run_id)

        for tp in runstat.periods.all():
            dts = DocTopic.objects.filter(
                run_id=run_id,
                doc__PY__in=tp.ys,
                score__gt=runstat.dt_threshold,
                topic__topicdtopic__dynamictopic__run_id=run_id,
                topic__topicdtopic__score__gt=runstat.dt_threshold
            ).values('topic__topicdtopic__dynamictopic__id')

            ipcc_annotate_dts(dts, run_id, tp)

        for topic in DynamicTopic.objects.filter(run_id=run_id):
            tdocs = Doc.objects.filter(
                doctopic__topic__topicdtopic__dynamictopic=topic,
                doctopic__topic__topicdtopic__score__gt=0.05,
                doctopic__score__gt=0.05
            )

            tdocs = tdocs.annotate(
                topic_combination = F('doctopic__score') * F('doctopic__topic__topicdtopic__score')
            )


            for wg in wgs:
                wgdocs = tdocs.filter(ipccref__wg__wg=wg["WG"])
                if wgdocs.count() == 0:
                    wg['score'] = 0
                else:
                    wg['score'] = wgdocs.aggregate(
                        s = Sum('topic_combination')
                    )['s']
            maxwg =  max(wgs, key=lambda x:x['score'])
            tscore = sum(x['score'] for x in wgs)
            if tscore==0:
                tscore=1
            topic.wg_1 = wgs[0]['score'] / tscore
            topic.wg_2 = wgs[1]['score'] / tscore
            topic.wg_3 = wgs[2]['score'] / tscore
            topic.primary_wg = maxwg['WG']
            #topic.wg_prop = maxwg['score'] / tscore
            topic.save()
    else:
        dts = DocTopic.objects.filter(
            run_id=run_id,
            doc__PY__lt=2014,
            score__gt=runstat.dt_threshold
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

        for topic in Topic.objects.filter(run_id=run_id):
            tdocs = Doc.objects.filter(doctopic__topic=topic,doctopic__score__gt=runstat.dt_threshold)
            for wg in wgs:
                wgdocs = tdocs.filter(ipccref__wg__wg=wg["WG"])
                if wgdocs.count() == 0:
                    wg['score'] = 0
                else:
                    wg['score'] = wgdocs.aggregate(s = Sum('doctopic__score'))['s']
            maxwg =  max(wgs, key=lambda x:x['score'])
            tscore = sum(x['score'] for x in wgs)
            if tscore==0:
                tscore=1
            topic.wg_1 = wgs[0]['score'] / tscore
            topic.wg_2 = wgs[1]['score'] / tscore
            topic.wg_3 = wgs[2]['score'] / tscore
            topic.primary_wg = maxwg['WG']
            topic.wg_prop = maxwg['score'] / tscore
            topic.save()

def update_primary_topic(run_id):
    return None
    runstat = RunStats.objects.get(pk=run_id)
    docs = Doc.objects.filter(query=runstat.query)
    docs = docs.filter(ipccref__isnull=False)
    for d in docs.iterator():
        t = Topic.objects.filter(
            doctopic__doc=d,
            run_id=run_id
        ).order_by('-doctopic__score').first()
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
