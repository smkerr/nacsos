import django
from django.utils import timezone
import urllib.parse
import os

import math
import threading, datetime
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")

django.setup()

from tmv_app.models import *
from scoping.models import Doc

def init(n_f,n_g):
    global run_id
    try:
        stats = RunStats.objects.all().last()
        settings = Settings.objects.all().first()
        run_id = stats.run_id
    except:
        settings = Settings(
            doc_topic_score_threshold=1,
            doc_topic_scaled_score=True
        )
        run_id = 0

    run_id +=1

    stats = RunStats(
        run_id = run_id,
        start=timezone.now(),
        batch_count=0,
        last_update=timezone.now(),
        ngram=n_g,
        max_features=n_f
    )
    stats.save()

    settings.run_id = run_id
    settings.save()

    return(run_id)

def increment_batch_count():
    django.db.connections.close_all()
    stats = RunStats.objects.get(run_id=run_id)
    stats.batch_count += 1
    stats.last_update = timezone.now()
    stats.topic_titles_current = False
    stats.topic_scores_current = False
    stats.topic_year_scores_current = False
    print ( stats.last_update )
    stats.save()


def add_terms(vocab):
    global term_diff
    for x in vocab:
        title = x[1]
        gid = x[0]
        term = Term(title=title,run_id=run_id)
        term.save()


def add_features(vocab):
    vocab_ids = []
    for x in range(len(vocab)):
        title = vocab[x]
        gid = x
        term, created = Term.objects.get_or_create(title=title)
        term.save()
        term.run_id.add(run_id)
        vocab_ids.append(term.pk)
    return(vocab_ids)

def add_topics(no_topics):
    global t_diff
    topic_ids = []
    for t in range(0,no_topics):
        title = "Topic " + str(t+1)
        topicrow = Topic(title=title,run_id=run_id)
        topicrow.save()
        topic_ids.append(topicrow.pk)
    return(topic_ids)

def update_topiccorr(topic_id,corrtopic,score,run_id):
    topic = Topic.objects.get(topic=topic_id)
    try:
        topiccorr = TopicCorr.objects.get(topic=topic, topiccorr=corrtopic, run_id=run_id)
    except:
        topiccorr = TopicCorr(topic=topic,topiccorr=corrtopic,run_id=run_id)
    topiccorr.score = score
    topiccorr.save()

def update_doccorr(doc_id,corrdoc,score,run_id):
    doc = Doc.objects.get(UT=topic_id)
    try:
        doccorr = DocCorr.objects.get(doc=doc, doccorr=corrdoc, run_id=run_id)
    except:
        doccorr = DocCorr(doc=doc, doccorr=corrdoc ,run_id=run_id)
    doccorr.score = score
    doccorr.save()

def docdiff(d):
    django.db.connections.close_all()
    last_doc = Doc.objects.all().last()
    doc_diff = last_doc.doc - d
    return(doc_diff)




def add_doc_topic_sk(doc_id, topic_id, score, scaled_score):
    if score < 0.001:
        return
    doc = Doc.objects.get(UT=doc_id)
    topic = Topic.objects.get(pk=topic_id)
    dt = DocTopic(doc=doc, topic=topic, score=score, scaled_score=scaled_score,run_id=run_id)
    dt.save()


def clear_topic_terms(topic):
    try:
        TopicTerm.objects.filter(topic=(topic),run_id=run_id).delete()
    except:
        return

def add_topic_term(topic_id, term_no, score):
    if score >= .005:
        topic = Topic.objects.get(topic=topic_id)
        term = Term.objects.get(term=term_no)
        tt = TopicTerm(topic=(topic), term=(term), score=score,run_id=run_id)
        tt.save()

def add_topic_term_sk(topic_id, term_no, score):
    if score >= .0005:
        topic = Topic.objects.get(pk=topic_id)
        term = Term.objects.get(pk=term_no)
        tt = TopicTerm(topic=(topic), term=(term), score=score,run_id=run_id)
        tt.save()
