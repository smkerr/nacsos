from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from django.db.models import Q, F, Sum, Count, FloatField, Case, When

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import csr_matrix, find
from functools import partial
from multiprocess import Pool
from utils.db import *
from utils.utils import *
from scoping.models import *
from time import time
import gc, sys, resource
from django.core import management
from utils.utils import flatten
import utils.db as db
from utils.text import *
import os


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

@shared_task
def do_nmf(run_id):
    stat = RunStats.objects.get(run_id=run_id)
    qid = stat.query.id
    K = stat.K

    TopicTerm.objects.filter(run_id=run_id).delete()
    DocTopic.objects.filter(run_id=run_id).delete()
    Topic.objects.filter(run_id=run_id).delete()

    for t in Term.objects.filter(run_id=run_id):
        t.run_id.remove(run_id)

    alpha = stat.alpha
    n_features = stat.max_features
    limit = stat.limit
    ng = stat.ngram
    n_samples = stat.max_iterations

    stat.process_id = os.getpid()
    stat.status = 1
    stat.save()

    docs = Doc.objects.filter(query=qid,content__iregex='\w')

    # if we are limiting, probably for testing, then do that
    if limit > 0:
        docs = docs[:limit]

    print('\n###############################\
    \n## Doing NMF on query {} with {} documents \
and {} topics\n'.format(qid, docs.count(),K))

    # Get the docs into lists
    abstracts, docsizes, ids = proc_docs(docs, stoplist)

    #############################################
    # Use tf-idf features for NMF.
    print("Extracting tf-idf features for NMF...")
    tfidf_vectorizer = TfidfVectorizer(
        max_df=0.97,
        min_df=stat.min_freq,
        max_features=n_features,
        ngram_range=(ng,ng),
        tokenizer=snowball_stemmer(),
        stop_words=stoplist
    )
    t0 = time()
    tfidf = tfidf_vectorizer.fit_transform(abstracts)
    print("done in %0.3fs." % (time() - t0))
    stat.tfidf_time = time() - t0
    stat.save()

    del abstracts
    gc.collect()


    vocab = tfidf_vectorizer.get_feature_names()
    vocab_ids = []
    pool = Pool(processes=8)
    vocab_ids.append(pool.map(partial(add_features,run_id=run_id),vocab))
    pool.terminate()
    del vocab
    vocab_ids = vocab_ids[0]


    ## Make some topics
    django.db.connections.close_all()
    topic_ids = db.add_topics(K, run_id)


    gc.collect()

    # Fit the NMF model
    print("Fitting the NMF model with tf-idf features, "
          "n_samples=%d and n_features=%d..."
          % (n_samples, n_features))
    t0 = time()
    nmf = NMF(n_components=K, random_state=1,
              alpha=alpha, l1_ratio=.5, verbose=True,
              init='nndsvd', max_iter=n_samples).fit(tfidf)

    print("done in %0.3fs." % (time() - t0))
    stat.nmf_time = time() - t0

    ## Add topics terms
    print("Adding topicterms to db")
    t0 = time()
    ldalambda = find(csr_matrix(nmf.components_))
    topics = range(len(ldalambda[0]))
    tts = []
    pool = Pool(processes=8)

    tts.append(pool.map(partial(db.f_lambda, m=ldalambda,
                    v_ids=vocab_ids,t_ids=topic_ids,run_id=run_id),topics))
    pool.terminate()
    tts = flatten(tts)
    gc.collect()
    sys.stdout.flush()
    django.db.connections.close_all()
    TopicTerm.objects.bulk_create(tts)
    print("done in %0.3fs." % (time() - t0))
    stat.db_time = stat.db_time + time() - t0


    ## Add topic-docs
    gamma =  find(csr_matrix(nmf.transform(tfidf)))
    glength = len(gamma[0])

    chunk_size = 100000

    ps = 16
    parallel_add = True

    all_dts = []

    make_t = 0
    add_t = 0

    t0 = time()
    ### Go through in chunks
    for i in range(glength//chunk_size+1):
        dts = []
        values_list = []
        f = i*chunk_size
        l = (i+1)*chunk_size
        if l > glength:
            l = glength
        docs = range(f,l)
        doc_batches = []
        for p in range(ps):
            doc_batches.append([x for x in docs if x % ps == p])
        pool = Pool(processes=ps)
        make_t0 = time()
        values_list.append(pool.map(partial(
            db.f_gamma_batch, gamma=gamma,
            docsizes=docsizes,docUTset=ids,topic_ids=topic_ids,
            run_id=run_id
        ),doc_batches))
        #dts.append(pool.map(partial(f_gamma, gamma=gamma,
        #                docsizes=docsizes,docUTset=ids,topic_ids=topic_ids),doc_batches))
        pool.terminate()
        make_t += time() - make_t0
        django.db.connections.close_all()

        add_t0 = time()
        values_list = [item for sublist in values_list for item in sublist]
        pool = Pool(processes=ps)
        pool.map(insert_many,values_list)
        pool.terminate()
        add_t += time() - add_t0
        gc.collect()
        sys.stdout.flush()

    stat.db_time = stat.db_time + time() - t0

    stat.error = nmf.reconstruction_err_
    stat.errortype = "Frobenius"
    stat.iterations = nmf.n_iter_
    stat.last_update=timezone.now()
    stat.status=3
    stat.save()
    management.call_command('update_run',run_id)
