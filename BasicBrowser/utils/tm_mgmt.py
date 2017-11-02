from tmv_app.models import *
from scoping.models import *

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
    #if "a" in "ab":
        dts = DynamicTopic.objects.filter(run_id=run_id).values_list('id',flat=True)
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
