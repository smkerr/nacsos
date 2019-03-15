import sys, resource, os, shutil, re, string, gc, subprocess
import django
from django.core.exceptions import MultipleObjectsReturned
import nltk
from multiprocess import Pool
from nltk.stem import SnowballStemmer
from nltk import word_tokenize
from time import time, sleep
from functools import partial
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, LatentDirichletAllocation

from scipy.sparse import csr_matrix, find
import numpy as np
from django.utils import timezone
from django.core import management
import platform


from tmv_app.models import *
from parliament.models import *
from scoping.models import Doc, Query
from django.db import connection, transaction
from utils.text import german_stemmer, snowball_stemmer, process_texts
import utils.db as db
from utils.utils import flatten
from nltk.corpus import stopwords
from parliament.utils import merge_utterance_paragraphs


# run the dynamic topic model with the algorithm by Blei
def run_blei_dtm(s_id, K, language="german", verbosity=1, extra_stopwords=set(), call_to_blei_algorithm=True,
                 max_features=20000, max_df=0.95, min_df=5, dtm_path="/home/galm/software/dtm/dtm/main"):

    t0 = time()

    s = Search.objects.get(pk=s_id)

    stat = RunStats(
        psearch=s,
        K=K,
        max_df=max_df,
        min_freq=min_df,
        method='BD', # BD = Blei dynamic topic model
        max_features=max_features,
        status=1
    )
    stat.save()
    run_id = stat.run_id

    ##########################
    ## create input and output folder

    input_path = './dtm-input-sid{}_{}'.format(s_id,stat.pk)
    output_path = './dtm-output-sid{}_{}'.format(s_id, stat.pk)

    if os.path.isdir(input_path):
        if call_to_blei_algorithm:
            shutil.rmtree(input_path)
            os.mkdir(input_path)
    else:
        os.mkdir(input_path)

    if os.path.isdir(output_path):
        if call_to_blei_algorithm:
            shutil.rmtree(output_path)
            os.mkdir(output_path)
    else:
        os.mkdir(output_path)

    # load text from database

    if s.search_object_type == 1:
        ps = Paragraph.objects.filter(search_matches=s)
        docs = ps.filter(text__iregex='\w').order_by('utterance__document__parlperiod__n')
        texts, docsizes, ids = process_texts(docs, stoplist, stat.fulltext)
        tc = ps.order_by().values('utterance__document__parlperiod__n'
                                  ).annotate(count = models.Count('utterance__document__parlperiod__n'))
        time_counts = {item['utterance__document__parlperiod__n']: item['count'] for item in tc}
        pps = ParlPeriod.objects.filter(document__utterance__in=uts).distinct()
        wps = ParlPeriod.objects.filter(document__utterance__paragraph__in=ps).distinct().values('n')

    elif s.search_object_type == 2:
        uts = Utterance.objects.filter(search_matches=s).order_by('document__parlperiod__n')
        texts, docsizes, ids = merge_utterance_paragraphs(uts)
        tc = uts.order_by().values('document__parlperiod__n'
                                   ).annotate(count = models.Count('document__parlperiod__n'))
        time_counts = {item['document__parlperiod__n']: item['count'] for item in tc}
        pps = ParlPeriod.objects.filter(document__utterance__in=uts).distinct()
        wps = ParlPeriod.objects.filter(document__utterance__in=uts).distinct().values('n')
    else:
        print("search object type invalid")
        return 1

    for i,pp in enumerate(pps.order_by('n')):
        try:
            tp, created = TimePeriod.objects.get_or_create(
                parlperiod=pp,
                n = i,
                ys = pp.years,
                title = str(pp)
            )
        except MultipleObjectsReturned:
            tp = TimePeriod.objects.filter(
                parlperiod=pp,
                n = i,
                ys = pp.years,
                title = str(pp)).order_by('id').first()
        stat.periods.add(tp)

    time_range = [s.n for s in stat.periods.all().order_by('n')]
<<<<<<< HEAD:BasicBrowser/utils/run_dtm_parliament.py
    time_range = sorted([wp['n'] for wp in wps])
=======
>>>>>>> ddfb5d5165d168f93609a3e48c6bf7f67fbed2eb:BasicBrowser/parliament/run_blei_dtm.py

    #########################
    ## Get the features now
    print("Extracting word features...")

    if language is "german":
        stemmer = SnowballStemmer("german")
        tokenizer = german_stemmer()
        stopword_list = [stemmer.stem(t) for t in stopwords.words("german")]

    elif language is "english":
        stemmer = SnowballStemmer("english")
        stopword_list = [stemmer.stem(t) for t in stopwords.words("english")]
        tokenizer = snowball_stemmer()
    else:
        print("Language not recognized.")
        return 1

    stopword_list = list(set(stopword_list) | set(extra_stopwords))

    vectorizer = CountVectorizer(max_df=stat.max_df,
                                 min_df=stat.min_freq,
                                 max_features=stat.max_features,
                                 ngram_range=(1 ,stat.ngram),
                                 tokenizer=tokenizer,
                                 stop_words=stopword_list)

    t0 = time()
    dtm = vectorizer.fit_transform(texts)

    print("done in %0.3fs." % (time() - t0))

    with open(os.path.join(input_path ,'foo-doctexts.dat') ,'w') as f:
        for i, text in enumerate(texts):
            f.write("D#{}: ".format(i) + text + "\n")
        f.write('\n')

    del texts

    gc.collect()

    print("Save terms to DB")

    # Get the vocab, add it to db
    vocab = vectorizer.get_feature_names()
    vocab_ids = []
    pool = Pool(processes=8)
    vocab_ids.append(pool.map(partial(db.add_features ,run_id=run_id) ,vocab))
    pool.terminate()

    vocab_ids = vocab_ids[0]
    with open(os.path.join(input_path ,'foo-vocab.dat') ,'w') as f:
        for i, w in enumerate(vocab):
            f.write(str(vocab_ids[i]) + ": " + w + "\n")
        f.write('\n')

    del vocab

    django.db.connections.close_all()

    print("write input files for Blei algorithm")

    with open(os.path.join(input_path ,'foo-mult.dat') ,'w') as mult:
        for d in range(dtm.shape[0]):
            words = find(dtm[d])
            uwords = len(words[0])
            mult.write(str(uwords) + " ")
            for w in range(uwords):
                index = words[1][w]
                count = words[2][w]
                mult.write(str(index ) +": " +str(count ) +" ")
            mult.write('\n')

    ##########################
    ##put counts per time step in the seq file

    with open(os.path.join(input_path, 'foo-seq.dat') ,'w') as seq:
        seq.write(str(len(time_range)))

        for key, value in time_counts.items():
            seq.write('\n')
            seq.write(str(value))

    ##########################
    # Run the dtm

    if call_to_blei_algorithm:
        print("Calling Blei algorithm")
        subprocess.Popen([
            dtm_path,
            "--ntopics={}".format(K),
            "--mode=fit",
            "--rng_seed=0",
            "--initialize_lda=true",
            "--corpus_prefix={}".format(os.path.join(os.path.abspath(input_path), 'foo')),
            "--outname={}".format(os.path.abspath(output_path)),
            "--top_chain_var=0.005",
            "--alpha={}".format(stat.alpha),
            "--lda_sequence_min_iter=10",
            "--lda_sequence_max_iter=20",
            "--lda_max_em_iter=20"
        ]).wait()
        print("Blei algorithm done")

    ##########################
    ## Upload the dtm results to the db

    print("upload dtm results to db")

    info = readInfo(os.path.join(output_path, "lda-seq/info.dat"))

    topic_ids = db.add_topics(stat.K, stat.run_id)

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

        if s.search_object_type == 1:
            pool.map(db.insert_many_pars, values_list)
        elif s.search_object_type == 2:
            pool.map(db.insert_many_utterances, values_list)

        pool.terminate()
        add_t += time() - add_t0
        gc.collect()
        sys.stdout.flush()

    stat = RunStats.objects.get(run_id=run_id)
    stat.last_update = timezone.now()
    stat.status = 3  # 3 = finished
    stat.save()
    management.call_command('update_run', run_id)

    totalTime = time() - t0

    tm = int(totalTime // 60)
    ts = int(totalTime - (tm * 60))

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")

    return 0



# ========================================================================================================
# utility functions for dynamic topic modeling (Blei and NMF)

# copied from ./import_lda.py
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

