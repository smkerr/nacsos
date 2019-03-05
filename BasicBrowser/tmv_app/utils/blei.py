import pickle, string, numpy, getopt, sys, random, time, re, pprint, gc, resource
import pandas as pd
import nltk, subprocess, psycopg2, math
from nltk.stem import SnowballStemmer
from nltk import word_tokenize
from multiprocess import Pool
import django
from functools import partial
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation
from time import time
from django.utils import timezone
from scipy.sparse import csr_matrix, find
import numpy as np
from django.core import management
import os

sys.stdout.flush()

# sys.path.append('/home/max/Desktop/django/BasicBrowser/')
import utils.db as db
from tmv_app.models import *
from scoping.models import *
from django.db import connection, transaction
from django.db.models import Count, Sum
from utils.text import *
#from tmv_app.utils.blei import readInfo, dtm_topic
cursor = connection.cursor()

def readInfo(p):
    d = {}
    with open(p) as f:
        for line in f:
            (key, val) = line.strip().split(' ',1)
            try:
                d[key] = int(val)
            except:
                d[key] = val
    return(d)

def dtm_topic(topic_n,info,topic_ids,vocab_ids,ys,run_id, output_path):
    print(topic_n)
    django.db.connections.close_all()
    p = "%03d" % (topic_n,)
    p = os.path.join(output_path, "lda-seq/topic-"+p+"-var-e-log-prob.dat")
    tlambda = np.fromfile(p, sep=" ").reshape((info['NUM_TERMS'],info['SEQ_LENGTH']))
    for t in range(len(tlambda)):
        for py in range(len(tlambda[t])):
            score = np.exp(tlambda[t][py])
            if score > 0.001:
                tt = TopicTerm(
                    topic_id = topic_ids[topic_n],
                    term_id = vocab_ids[t],
                    PY = ys[py],
                    score = score,
                    run_id=run_id
                )
                tt.save()
                #db.add_topic_term(topic_n+info['first_topic'], t+info['first_word'], py, score)
    django.db.connections.close_all()

def upload_dtm(run_id, output_path):
    stat = RunStats.objects.get(pk=run_id)
    print("upload dtm results to db")

    info = readInfo(os.path.join(output_path, "lda-seq/info.dat"))

    topic_ids = db.add_topics(stat.K, stat.run_id)

    vocab_ids = []
    input_path = output_path.replace("-output-","-input-")
    with open(os.path.join(input_path ,'foo-vocab.dat') ,'r') as f:
        for l in f:
            try:
                vocab_ids.append(int(l.split(':')[0].strip()))
            except:
                pass

    ids = []
    docsizes = []
    with open(os.path.join(input_path ,'foo-docids.dat') ,'r') as f:
        for l in f:
            try:
                id, s = [int(x.strip()) for x in l.split(':')]
                ids.append(id)
                docsizes.append(s)
            except:
                pass

    time_range = sorted([tp.n for tp in stat.periods.all().order_by('n')])

    #################################
    # TopicTerms

    print("writing topic terms")
    topics = range(info['NUM_TOPICS'])
    pool = Pool(processes=8)
    pool.map(partial(
        dtm_topic,
        info=info,
        topic_ids=topic_ids,
        vocab_ids=vocab_ids,
        ys = time_range,
        run_id=run_id,
        output_path=output_path
    ) ,topics)
    pool.terminate()
    gc.collect()

    ######################################
    # Doctopics
    print("writing doctopics")
    gamma = np.fromfile(os.path.join(output_path, 'lda-seq/gam.dat'), dtype=float ,sep=" ")
    gamma = gamma.reshape((int(len(gamma ) /stat.K) ,stat.K))

    gamma = find(csr_matrix(gamma))
    glength = len(gamma[0])
    chunk_size = 100000
    ps = 16
    parallel_add = True

    all_dts = []

    make_t = 0
    add_t = 0

    for i in range(glength//chunk_size +1):
        dts = []
        values_list = []
        f = i* chunk_size
        l = (i + 1) * chunk_size
        if l > glength:
            l = glength
        docs = range(f, l)
        doc_batches = []
        for p in range(ps):
            doc_batches.append([x for x in docs if x % ps == p])
        pool = Pool(processes=ps)
        make_t0 = time()
        values_list.append(pool.map(partial(db.f_gamma_batch, gamma=gamma,
                                            docsizes=docsizes, docUTset=ids, topic_ids=topic_ids, run_id=run_id),
                                    doc_batches))
        pool.terminate()
        make_t += time() - make_t0
        django.db.connections.close_all()

        add_t0 = time()
        values_list = [item for sublist in values_list for item in sublist]

        pool = Pool(processes=ps)
        pool.map(db.insert_many, values_list)
        pool.terminate()

        add_t += time() - add_t0
        gc.collect()
        sys.stdout.flush()

    stat = RunStats.objects.get(run_id=run_id)
    stat.last_update = timezone.now()
    stat.status = 3  # 3 = finished
    stat.save()
    management.call_command('update_run', run_id)
