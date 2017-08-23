from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from django.db.models import Q, F, Sum, Count, FloatField, Case, When

@shared_task
def update_dtopic(topic_id, parent_run_id):
    topic = DynamicTopic.objects.get(pk=topic_id)
    ## Write the title from the top terms
    topicterms = Term.objects.filter(
        dynamictopicterm__topic=topic,
        dynamictopicterm__PY__isnull=True
    ).order_by('-dynamictopicterm__score')[:10]
    topic.top_words=[x.title.lower() for x in topicterms]
    new_topic_title = '{'
    new_topic_title+= ', '.join([tt.title for tt in topicterms[:3]])
    new_topic_title+='}'
    topic.title = new_topic_title
    topic.score = 0
    #
    score = DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__primary_dtopic=topic
    ).annotate(
        dtopic_score = F('score') * F('topic__topicdtopic__score')
    ).aggregate(
        t=Sum('dtopic_score')
    )['t']
    maxyear = DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__primary_dtopic=topic
    ).order_by('-topic__year')[0].topic.year
    if score is not None:
        topic.score = score
    l1score = DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__primary_dtopic=topic,
        topic__year= maxyear
    ).annotate(
        dtopic_score = F('score') * F('topic__topicdtopic__score')
    ).aggregate(
        t=Sum('dtopic_score')
    )['t']
    if l1score is not None:
        topic.l1ys = l1score / score
    l5score = DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__primary_dtopic=topic,
        topic__year__gt= maxyear-5
    ).annotate(
        dtopic_score = F('score') * F('topic__topicdtopic__score')
    ).aggregate(
        t=Sum('dtopic_score')
    )['t']
    if l5score is not None:
        topic.l5ys = l5score / score
    topic.save()

@shared_task
def yearly_topic_term(topic_id, run_id):
    dt = DynamicTopic.objects.get(pk=topic_id)

    stat=RunStats.objects.get(pk=run_id)
    if stat.parent_run_id is not None:
        parent_run_id = stat.parent_run_id
    else:
        parent_run_id = run_id

    years = list(Topic.objects.filter(
        run_id_id=parent_run_id
    ).distinct('year').values_list('year',flat=True))
    for y in years:
        ytts = TopicTerm.objects.filter(
            topic__year=y,
            topic__topicdtopic__dynamictopic=dt
        )
        if ytts.count() > 0:
            ytts = ytts.annotate(
                dtopic_score = F('score') * F('topic__topicdtopic__score')
            ).filter(
                dtopic_score__gt=0.01
            ).order_by('-dtopic_score')[:100]
        for ytt in ytts:
            dtt, created = DynamicTopicTerm.objects.get_or_create(
                topic=dt,
                term=ytt.term,
                PY=y,
                run_id=run_id,
                score=ytt.dtopic_score
            )
            #dtt.score =
            dtt.save()

        ############
        ## Calculate year score for this topic
        ytds = DocTopic.objects.filter(
            topic__year=y,
            topic__topicdtopic__dynamictopic=dt
        ).annotate(
            dtopic_score = F('score') * F('topic__topicdtopic__score')
        ).aggregate(
            yscore = Sum('dtopic_score')
        )['yscore']

        ##########
        ## Create dty objects
        dty, created = DynamicTopicYear.objects.get_or_create(
            topic=dt,
            PY=y,
            run_id=run_id
        )
        if ytds is None:
            ytds = 0
        dty.score=ytds
        dty.save()
