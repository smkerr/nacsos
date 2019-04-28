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

# ===============================================================================================================
# ===============================================================================================================


# run dynamic nmf
def run_dynamic_nmf(stat):
    """
    Run dynamic NMF model on utterances (speeches) or paragraphs from the parliament data

    :param stat: RunStats object with the parameters to run the model with
    :return: 0 if successful, 1 otherwise
    """

    print("starting topic model for runstat with settings:")
    for field in stat._meta.fields:
        field_value = getattr(stat, field.name)
        if field_value:
            print("{}: {}".format(field.name, field_value))

    t0 = time()
    start_datetime = timezone.now()

    s = Search.objects.get(pk=stat.psearch.id)

    n_samples = 1000

    run_id = stat.run_id

    # load time range
    if s.search_object_type == 1:
        ps = Paragraph.objects.filter(search_matches=s)
        wps = ParlPeriod.objects.filter(document__utterance__paragraph__in=ps).distinct().values('n')

    elif s.search_object_type == 2:
        uts = Utterance.objects.filter(search_matches=s).order_by('document__parlperiod__n')
        wps = ParlPeriod.objects.filter(document__utterance__in=uts).distinct().values('n')
    else:
        print("search object type invalid")
        return 1

    # language specific settings
    if stat.language is "german":
        stemmer = SnowballStemmer("german")
        tokenizer = german_stemmer()
        stopword_list = [stemmer.stem(t) for t in stopwords.words("german")]

    elif stat.language is "english":
        stemmer = SnowballStemmer("english")
        stopword_list = [stemmer.stem(t) for t in stopwords.words("english")]
        tokenizer = snowball_stemmer()
    else:
        print("Language not recognized.")
        return 1

    if stat.extra_stopwords:
        stopword_list = list(set(stopword_list) | set(stat.extra_stopwords))


    time_range = sorted([wp['n'] for wp in wps])

    for timestep in time_range:

        # load text from database
        if s.search_object_type == 1:
            ps = Paragraph.objects.filter(search_matches=s, utterance__document__parlperiod__n=timestep)
            docs = ps.filter(text__iregex='\w')
            texts, docsizes, ids = process_texts(docs, stoplist, stat.fulltext)

        elif s.search_object_type == 2:
            uts = Utterance.objects.filter(search_matches=s, document__parlperiod__n=timestep)
            texts, docsizes, ids = merge_utterance_paragraphs(uts)
        else:
            print("search object type not known")
            return 1

        print("\n#######################")
        print("in period {}: {} docs".format(timestep, len(texts)))
        k = stat.K
        # k = predict(text_count)
        # print("esimating {} topics...".format(k))

        print("Extracting tf-idf features for NMF...")
        tfidf_vectorizer = TfidfVectorizer(max_df=stat.max_df,
                                           min_df=stat.min_freq,
                                           max_features=stat.max_features,
                                           ngram_range=(1, stat.ngram),
                                           tokenizer=tokenizer,
                                           stop_words=stopword_list)

        t1 = time()
        tfidf = tfidf_vectorizer.fit_transform(texts)
        del texts
        gc.collect()

        print("done in %0.3fs." % (time() - t1))

        print("Save terms to DB")

        # Get the vocab, add it to db
        vocab = tfidf_vectorizer.get_feature_names()
        vocab_ids = []
        pool = Pool(processes=8)
        vocab_ids.append(pool.map(partial(db.add_features, run_id=run_id), vocab))
        pool.terminate()
        del vocab
        vocab_ids = vocab_ids[0]

        django.db.connections.close_all()
        topic_ids = db.add_topics(k, run_id)
        for t in topic_ids:
            top = Topic.objects.get(pk=t)
            top.year = timestep
            top.save()

        gc.collect()

        # Fit the NMF model
        print("Fitting the NMF model with tf-idf features, "
              "n_samples=%d and max_features=%d..."
              % (n_samples, stat.max_features))
        t1 = time()
        nmf = NMF(n_components=k, random_state=1,
                  alpha=.0001, l1_ratio=.5).fit(tfidf)
        print("done in %0.3fs." % (time() - t1))

        print("Adding topicterms to db")
        ldalambda = find(csr_matrix(nmf.components_))
        topics = range(len(ldalambda[0]))
        tts = []
        pool = Pool(processes=8)

        tts.append(pool.map(partial(db.f_lambda, m=ldalambda,
                                    v_ids=vocab_ids, t_ids=topic_ids, run_id=run_id), topics))
        pool.terminate()
        tts = flatten(tts)
        gc.collect()
        sys.stdout.flush()
        django.db.connections.close_all()
        TopicTerm.objects.bulk_create(tts)
        print("done in %0.3fs." % (time() - t1))

        gamma = find(csr_matrix(nmf.transform(tfidf)))
        glength = len(gamma[0])

        chunk_size = 100000

        no_cores = 16

        make_t = 0
        add_t = 0

        ### Go through in chunks
        for i in range(glength // chunk_size + 1):
            values_list = []
            f = i * chunk_size
            l = (i + 1) * chunk_size
            if l > glength:
                l = glength
            docs = range(f, l)
            doc_batches = []
            for p in range(no_cores):
                doc_batches.append([x for x in docs if x % no_cores == p])
            pool = Pool(processes=no_cores)
            make_t0 = time()
            values_list.append(pool.map(partial(db.f_gamma_batch, gamma=gamma,
                                                docsizes=docsizes, docUTset=ids,
                                                topic_ids=topic_ids, run_id=run_id),
                                        doc_batches))
            pool.terminate()
            make_t += time() - make_t0
            django.db.connections.close_all()

            add_t0 = time()
            values_list = [item for sublist in values_list for item in sublist]
            pool = Pool(processes=no_cores)

            if s.search_object_type == 1:
                pool.map(db.insert_many_pars, values_list)
            elif s.search_object_type == 2:
                pool.map(db.insert_many_utterances, values_list)

            pool.terminate()
            add_t += time() - add_t0
            gc.collect()
            sys.stdout.flush()

        stat.error = stat.error + nmf.reconstruction_err_
        stat.errortype = "Frobenius"

    ## After all the years have been run, update the dtops

    tops = Topic.objects.filter(run_id=run_id)

    highest_id = Term.objects.all().order_by('-id').first().id
    B = np.zeros((tops.count(), highest_id))

    #print(tops)

    wt = 0
    for topic in tops:
        tts = TopicTerm.objects.filter(
            topic=topic
        ).order_by('-score')[:50]
        for tt in tts:
            B[wt, tt.term.id] = tt.score
        wt += 1

    col_sum = np.sum(B, axis=0)
    vocab_ids = np.flatnonzero(col_sum)

    # we only want the columns where there are at least some
    # topic-term values
    B = B[:, vocab_ids]

    nmf = NMF(
        n_components=stat.K, random_state=1,
        alpha=.1, l1_ratio=.5
    ).fit(B)

    ## Add dynamic topics
    dtopics = []
    for k in range(stat.K):
        dtopic = DynamicTopic(
            run_id=RunStats.objects.get(pk=run_id)
        )
        dtopic.save()
        dtopics.append(dtopic)

    dtopic_ids = list(
        DynamicTopic.objects.filter(
            run_id=run_id
        ).values_list('id', flat=True)
    )

    print(dtopic_ids)

    ##################
    ## Add the dtopic*term matrix to the db
    print("Adding topicterms to db")
    t1 = time()
    ldalambda = find(csr_matrix(nmf.components_))
    topics = range(len(ldalambda[0]))
    tts = []
    pool = Pool(processes=8)
    tts.append(pool.map(partial(db.f_dlambda, m=ldalambda,
                                v_ids=vocab_ids, t_ids=dtopic_ids, run_id=run_id), topics))
    pool.terminate()
    tts = flatten(tts)
    gc.collect()
    sys.stdout.flush()
    django.db.connections.close_all()
    DynamicTopicTerm.objects.bulk_create(tts)
    print("done in %0.3fs." % (time() - t1))

    ## Add the wtopic*dtopic matrix to the database
    gamma = nmf.transform(B)

    for topic in range(len(gamma)):
        for dtopic in range(len(gamma[topic])):
            if gamma[topic][dtopic] > 0:
                tdt = TopicDTopic(
                    topic=tops[topic],
                    dynamictopic_id=dtopic_ids[dtopic],
                    score=gamma[topic][dtopic]
                )
                tdt.save()

    ## Calculate the primary dtopic for each topic
    for t in tops:
        try:
            t.primary_dtopic.add(TopicDTopic.objects.filter(
                topic=t
            ).order_by('-score').first().dynamictopic)
            t.save()
        except:
            print("saving primary topic not working")
            pass

    management.call_command('update_run', run_id)

    stat.error = stat.error + nmf.reconstruction_err_
    stat.errortype = "Frobenius"
    stat.last_update = timezone.now()
    stat.runtime = timezone.now() - start_datetime
    stat.status = 3  # 3 = finished
    stat.save()

    totalTime = time() - t0

    tm = int(totalTime // 60)
    ts = int(totalTime - (tm * 60))

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")

    return 0
