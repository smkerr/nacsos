from tmv_app.models import *
from scoping.models import *
from django.utils import timezone
import django
from django.db import connection, transaction
cursor = connection.cursor()
from psycopg2.extras import *

def add_features(title, run_id):
    django.db.connections.close_all()
    try:
        term, created = Term.objects.get_or_create(title=title)
    except:
        ts = Term.objects.filter(title=title).order_by('id')
        if ts.count() > 0:
            ts.last().delete()
        term = ts.first()
    term.run_id.add(run_id)
    django.db.connections.close_all()
    return term.pk

def add_topics(no_topics, run_id):
    topic_ids = []
    for t in range(0,no_topics):
        title = "Topic " + str(t+1)
        topicrow = Topic(title=title,run_id_id=run_id)
        topicrow.save()
        topic_ids.append(topicrow.pk)
    return(topic_ids)

def f_lambda(t,m,v_ids,t_ids,run_id):
    tt = TopicTerm(
        term_id = v_ids[m[1][t]],
        topic_id = t_ids[m[0][t]],
        score = m[2][t],
        run_id = run_id
    )
    return tt

def insert_many_old(values_list):
    query='''
        INSERT INTO "tmv_app_doctopic"
        ("doc_id", "topic_id", "score", "scaled_score", "run_id")
        VALUES (%s,%s,%s,%s,%s)
    '''
    cursor = connection.cursor()
    cursor.executemany(query,values_list)

def insert_many(values_list):
    cursor = connection.cursor()
    execute_values(
        cursor,
        "INSERT INTO tmv_app_doctopic (doc_id, topic_id, score, scaled_score, run_id) VALUES %s",
        values_list
    )

def insert_many_pars(values_list):
    cursor = connection.cursor()
    execute_values(
        cursor,
        "INSERT INTO tmv_app_doctopic (par_id, topic_id, score, scaled_score, run_id) VALUES %s",
        values_list
    )

def f_dlambda(t,m,v_ids,t_ids,run_id):
    tt = DynamicTopicTerm(
        term_id = v_ids[m[1][t]],
        topic_id = t_ids[m[0][t]],
        score = m[2][t],
        run_id = run_id
    )
    return tt


def init(n_f):
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
        ngram=1,
        max_features=n_f
    )
    stats.save()

    settings.run_id = run_id
    settings.save()

    return(run_id)


def f_gamma_batch(docs,gamma,docsizes,docUTset,topic_ids,run_id):
    vl = []
    for d in docs:
        dt = (
            docUTset[gamma[0][d]],
            topic_ids[gamma[1][d]],
            gamma[2][d],
            gamma[2][d] / docsizes[gamma[0][d]],
            run_id
        )
        vl.append(dt)
    return vl
