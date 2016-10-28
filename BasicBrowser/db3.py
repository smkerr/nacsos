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

def init():
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
        last_update=timezone.now()
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
    term_diff = term.term - gid
   

def add_topics(no_topics):
    global t_diff
    for t in range(0,no_topics):
        title = "Topic " + str(t+1)
        topicrow = Topic(title=title,run_id=run_id)
        topicrow.save()
    t_diff = topicrow.topic - t


def add_doc(title,content,docID,UT,PY,AU):
    doc = Doc(title=urllib.parse.unquote(title), content=urllib.parse.unquote(content),UT=UT,PY=PY,run_id=run_id)
    doc.save()
    AUlist = str(AU)
    for au in AUlist.split("\n"):
        docauth = DocAuthors(doc=doc,author=au.strip(),run_id=run_id)
        docauth.save()

def docdiff(d):
    django.db.connections.close_all()
    last_doc = Doc.objects.all().last()
    doc_diff = last_doc.doc - d
    return(doc_diff)


def add_doc_topic(doc_id, topic_id, score, scaled_score):
    if score < 1:
        return
    topic_id = topic_id+t_diff
    doc = Doc.objects.get(doc=doc_id)
    topic = Topic.objects.get(topic=topic_id)
    dt = DocTopic(doc=doc, topic=topic, score=score, scaled_score=scaled_score,run_id=run_id)
    dt.save()


def clear_topic_terms(topic):
    topic = topic+t_diff
    try:
        TopicTerm.objects.filter(topic=(topic),run_id=run_id).delete()
    except:
        return

def add_topic_term(topic_id, term_no, score):
    if score >= .005:
        topic_id = topic_id+t_diff
        term_no += term_diff
        topic = Topic.objects.get(topic=topic_id)
        term = Term.objects.get(term=term_no)
        tt = TopicTerm(topic=(topic), term=(term), score=score,run_id=run_id)
        tt.save()



