from __future__ import absolute_import, unicode_literals
from celery import shared_task
from parliament.models import *
from cities.models import Region
from tmv_app.models import *
from utils.utils import *
import os
from utils.text import german_stemmer, snowball_stemmer, proc_texts
from utils.tm_mgmt import *
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import csr_matrix, find
from sklearn.decomposition import NMF, LatentDirichletAllocation as LDA
import random
import utils.db as db
from multiprocess import Pool
from functools import partial
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords


@shared_task
def do_search(s):
    s = Search.objects.get(pk=s)
    ps = Paragraph.objects.filter(text__iregex=s.text)
    print("{} paragraphs with search {}".format(ps.count(), s.text))

    # filter for parties
    if s.party is not None:
        ps = ps.filter(utterance__speaker__party=s.party)
        print("{} paragraphs left after filtering for party: {}".format(ps.count(), s.party))

    # filter for regions
    if s.speaker_regions.exists():
        if s.speaker_regions.exists():
            # differentiate between different seat types (list or direct mandate):
            # list: speaker -> seat -> partylist -> region
            ps_list = ps.filter(utterance__speaker__seat__seat_type=2).distinct()
            ps_list = ps_list.filter(utterance__speaker__seat__list__region__in=s.speaker_regions.all())
            print("paragraphs attributed to list mandates in regions: {}".format(ps_list.count()))

            # direct: speaker -> seat -> consituency -> region
            ps_direct = ps.filter(utterance__speaker__seat__seat_type=1).distinct()
            ps_direct = ps_direct.filter(utterance__speaker__seat__constituency__region__in=s.speaker_regions.all())
            ps = ps_list.union(ps_direct)
            print("paragraphs attributed to direct mandates in regions: {}".format(ps_direct.count()))

            print("{} paragraphs left after filtering for regions: {}".format(ps.count(), [r.name for r in s.speaker_regions.all()]))

    Through = Paragraph.search_matches.through
    tms = [Through(paragraph=p,search=s) for p in ps]
    Through.objects.bulk_create(tms)
    s.par_count=ps.count()
    s.save()
    return tms


@shared_task
def run_tm(s, K, language="german", verbosity=1):
    s = Search.objects.get(pk=s)
    #RunStats.objects.filter(psearch=s).delete()
    ps = Paragraph.objects.filter(search_matches=s).filter()

    stat = RunStats(
        psearch=s,
        K=K,
        min_freq=5,

    )
    stat.save()
    run_id=stat.run_id

    if verbosity > 0:
        print("creating term frequency-inverse document frequency matrix")
    docs = ps.filter(text__iregex='\w')
    abstracts, docsizes, ids = proc_texts(docs, stoplist, stat.fulltext)
    doc_ids = ids
    if stat.max_features == 0:
        n_features=1000000
    else:
        n_features = stat.max_features

    if language is "german":
        stemmer = SnowballStemmer("german")
        german_stopwords = [stemmer.stem(t) for t in stopwords.words("german")]
        # get term frequency-inverse document frequency matrix (using log weighting)
        # and min/max document frequency (min_df, max_df)

        tfidf_vectorizer = TfidfVectorizer(
            max_df=stat.max_df,
            min_df=stat.min_freq,
            max_features=n_features,
            ngram_range=(stat.ngram,stat.ngram),
            tokenizer=german_stemmer(),
            stop_words=german_stopwords
        )
    elif language is "english":
        stemmer = SnowballStemmer("english")
        stopword_list = [stemmer.stem(t) for t in stopwords.words("english")]
        tfidf_vectorizer = TfidfVectorizer(
            max_df=stat.max_df,
            min_df=stat.min_freq,
            max_features=n_features,
            ngram_range=(stat.ngram,stat.ngram),
            tokenizer=snowball_stemmer(),
            stop_words=stopword_list
        )
    else:
        raise KeyError("Language not set correctly.")


    tfidf = tfidf_vectorizer.fit_transform(abstracts)
    vectorizer = tfidf_vectorizer

    vocab = vectorizer.get_feature_names()
    vocab_ids = []

    if verbosity > 0:
        print("save terms to db")

    # multiprocessing: add vocabulary as Term
    pool = Pool(processes=8)
    vocab_ids.append(pool.map(partial(db.add_features,run_id=run_id),vocab))
    pool.terminate()
    del vocab
    vocab_ids = vocab_ids[0]

    ## Make some topics
    django.db.connections.close_all()
    topic_ids = db.add_topics(K, run_id)
    gc.collect()

    if verbosity > 0:
        v=True
    else:
        v=False

    if verbosity > 0:
        print("running matrix factorization")
    # NMF = non-negative matrix factorization
    model = NMF(
        n_components=K, random_state=1,
        alpha=stat.alpha, l1_ratio=.1, verbose=v,
        init='nndsvd', max_iter=stat.max_iterations
    ).fit(tfidf)
    dtm = csr_matrix(model.transform(tfidf))

    # term topic matrix
    ldalambda = find(csr_matrix(model.components_))
    # find returns the indices and values of the nonzero elements of a matrix
    topics = range(len(ldalambda[0]))
    tts = []

    # multiprocessing: add TopicTerms and scores
    pool = Pool(processes=8)
    tts.append(pool.map(partial(db.f_lambda, m=ldalambda,
                    v_ids=vocab_ids,t_ids=topic_ids,run_id=run_id),topics))
    pool.terminate()

    tts = flatten(tts)
    gc.collect()
    sys.stdout.flush()
    django.db.connections.close_all()
    TopicTerm.objects.bulk_create(tts)

    if verbosity > 0:
        print("saving docuemt topic matrix to db")

    #document topic matrix
    gamma = find(dtm)
    glength = len(gamma[0])

    chunk_size = 100000

    ps = 16
    parallel_add = True

    all_dts = []

    make_t = 0
    add_t = 0

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
        values_list.append(pool.map(partial(
            db.f_gamma_batch, gamma=gamma,
            docsizes=docsizes,docUTset=ids,topic_ids=topic_ids,
            run_id=run_id
        ),doc_batches))
        pool.terminate()
        django.db.connections.close_all()
        values_list = [item for sublist in values_list for item in sublist]
        pool = Pool(processes=ps)
        pool.map(db.insert_many_pars,values_list)
        pool.terminate()
        gc.collect()
        sys.stdout.flush()

    stat.status = 3  # 3 = finished
    stat.save()
    update_topic_titles(run_id)

    if verbosity > 0:
        print("topic model run done")

    return 0

