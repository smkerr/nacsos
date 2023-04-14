from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from django.db.models import Q, F, Sum, Count, FloatField, Case, When

import lda

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, LatentDirichletAllocation as LDA
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy.sparse import csr_matrix, find, lil_matrix
from functools import partial
#from multiprocessing import Pool
from billiard import Pool
from utils.db import *
from utils.utils import *
from scoping.models import *
import parliament.models as pm
from time import time
import gc, sys, resource
from django.core import management
from utils.utils import flatten
import utils.db as db
from utils.text import *
import os
import gensim
import random
from sklearn.decomposition._nmf import _beta_divergence  # needs sklearn 0.19!!!
from sklearn.preprocessing import RobustScaler
from django.db import connection, transaction
from psycopg2.extras import *
import tmv_app.utils.warplda as wpu

@shared_task
def create_topic_assessments(run_id, uids, n_docs):
    '''
    Create WordIntrusions and TopicIntrusions for the users
    in uids and the number of docs n_docs
    '''
    # Get a unique docs that have a doctopic in this model and take a random sample
    docs = set(DocTopic.objects.filter(
        run_id=run_id
    ).values_list('doc__pk', flat=True))
    docs = random.sample(docs, n_docs)
    stat = RunStats.objects.get(pk=run_id)
    users = User.objects.filter(pk__in=uids)
    for u in users:
        for d in docs:
            doc = Doc.objects.get(pk=d)
            doc.create_topicintrusion(u, run_id)
        for t in stat.topic_set.all():
            t.create_wordintrusion(u)
    return


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

    all_scores = DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__topicdtopic__dynamictopic=topic
    ).annotate(
        dtopic_score = F('score') * F('topic__topicdtopic__score')
    )

    ddts = DocDynamicTopic.objects.filter(
        run_id=parent_run_id,
        topic__id=topic_id
    )
    if ddts.count() == 0:

        cursor = connection.cursor()
        dts = DocTopic.objects.filter(
            run_id=parent_run_id,
            topic__topicdtopic__dynamictopic=topic
        ).values('doc__id').annotate(
            dtopic_score = Sum(F('score') * F('topic__topicdtopic__score'))
        ).filter(dtopic_score__gt=0.01)

        values_list = [(x['doc__id'],topic_id,x['dtopic_score'],parent_run_id) for x in dts]

        execute_values(
            cursor,
            "INSERT INTO tmv_app_docdynamictopic (doc_id, topic_id, score, run_id) VALUES %s",
            values_list
        )

    score = all_scores.aggregate(
        t=Sum('dtopic_score')
    )['t']
    stats = topic.run_id

    ptdt = None # Previous tdt
    for tp in stats.periods.all().order_by('n'):

        dtot, created = TimeDocTotal.objects.get_or_create(
            period=tp,
            run=stats
        )
        tdt, created = TimeDTopic.objects.get_or_create(
            period = tp,
            dtopic=topic
        )

        tdt.score = all_scores.filter(
            doc__PY__in=tp.ys
        ).aggregate(
            t=Sum('dtopic_score')
        )['t']
        if tdt.score is not None:
            tdt.share = tdt.score / dtot.dt_score
        else:
            tdt.score = 0
            tdt.share = 0
        tdt.save()
        if ptdt:
            if ptdt.score == 0 or ptdt.score is None:
                tdt.pgrowth=0
            else:
                tdt.pgrowth = (tdt.score - ptdt.score) / ptdt.score * 100
            tdt.save()
        ptdt = tdt

    if len(DocTopic.objects.filter(
        run_id=parent_run_id,
        topic__primary_dtopic=topic)) > 0:

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
    else:
        print("No DocTopics found for {}".format(topic))

    topic.save()

    return topic.id

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
                dtopic_score__gt=0.001
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

@shared_task
def get_coherence(run_id):
    """
    Calculates the coherence for a topic model

    :param run_id: id of the topic model
    :return:
    """

    stat = RunStats.objects.get(run_id=run_id)
    K = stat.K

    if stat.query != None:
        qid = stat.query.id

        if stat.fulltext:
            docs = Doc.objects.filter(query=qid,fulltext__iregex='\w')
        else:
            docs = Doc.objects.filter(query=qid,content__iregex='\w')

        abstracts, docsizes, ids = proc_docs(docs, stoplist, stat.fulltext)

        sentences = [get_sentence(x) for x in abstracts]

    elif stat.psearch != None:
        sid = stat.psearch.id
        uts = pm.Utterance.objects.filter(search_matches=sid)
        texts = []
        for ut in uts:
            pars = ut.paragraph_set.all()
            texts.append(" ".join([x.text for x in pars]))

        sentences = [get_sentence_g(x) for x in texts]

    model = gensim.models.Word2Vec(sentences)
    validation_measure = WithinTopicMeasure(
        ModelSimilarity(model)
    )

    term_rankings = []

    topics = Topic.objects.filter(
        run_id=run_id
    )

    for topic in topics:
        term_ranking = list(Term.objects.filter(
            topicterm__topic=topic
        ).order_by(
            '-topicterm__score'
        ).values_list('title',flat=True)[:50])
        term_rankings.append(term_ranking)

    stat.coherence = validation_measure.evaluate_rankings(
        term_rankings
    )
    stat.save()

    return


@shared_task
def get_exclusivity(run_id, word_num=10, frex_w=.7):
    """
    Calculates exclusivity for a topic model based on the association between word and topic

    Adapted from exclusivity function from stm package in R
    """
    stat = RunStats.objects.get(run_id=run_id)
    K = stat.K
    w = frex_w

    # create a dataframe from run_id
    tts = TopicTerm.objects.filter(run_id=run_id)

    tts_n = tts.values('topic__id').annotate(
        n = Sum('score'),
        term = F('term__title')
    ).order_by('topic', '-n')

    df = pd.DataFrame.from_dict(list(tts_n))

    df_p = df.pivot(index='topic__id', columns='term', values='n')
    df_p2 = df.pivot(index='term', columns='topic__id', values='n')

    # normalise by sum of terms across topics
    df_p_sum = df_p.sum(axis=0)
    mat = df_p/df_p_sum
    mat = mat.transpose()

    # find exclusivity by dividing individual TopicTerm score by sum of score of Term across all topics
    ex = mat.rank(axis=1)/mat.count(axis=0)
    fr = df_p2.rank(axis=1)/df_p2.count(axis=0)

    # calculate frex using formula specified
    frex = 1/((w/ex)+((1-w)/fr))

    # sort frex results by descending values in each column, and extract n results based on pre-defined number
    frex_sort = -np.sort(-frex.values, axis=0)[1:word_num]
    frex_sort0 = np.nan_to_num(frex_sort)

    # return as sum of frex scores for top 10 terms in all topics
    out = [None]*K

    for i in range(0,K):
        out[i] = sum(frex_sort0[:,i])

    out_sum = sum(out)

    # normalise by topic number
    exclusivity = out_sum/K

    stat.exclusivity = exclusivity
    stat.save()


@shared_task
def k_fold(run_id,k_folds):
    stat = RunStats.objects.get(run_id=run_id)
    qid = stat.query.id
    K = stat.K
    alpha = stat.alpha
    n_features = stat.max_features
    if n_features == 0:
        n_features = 100000000000
    limit = stat.limit
    ng = stat.ngram

    if stat.method=="LD":
        if stat.max_iter == 200:
            stat.max_iter = 10
        if stat.max_iter > 100:
            stat.max_iter = 90

    n_samples = stat.max_iter

    if stat.fulltext:
        docs = Doc.objects.filter(query=qid,fulltext__iregex='\w')
    else:
        docs = Doc.objects.filter(query=qid,content__iregex='\w')

    # if we are limiting, probably for testing, then do that
    if limit > 0:
        docs = docs[:limit]


    tfidf_vectorizer = TfidfVectorizer(
        max_df=stat.max_df,
        min_df=stat.min_freq,
        max_features=n_features,
        ngram_range=(ng,ng),
        tokenizer=snowball_stemmer(),
        stop_words=list(stoplist)
    )

    count_vectorizer = CountVectorizer(
        max_df=stat.max_df,
        min_df=stat.min_freq,
        max_features=n_features,
        ngram_range=(ng,ng),
        tokenizer=snowball_stemmer(),
        stop_words=list(stoplist)
    )

    abstracts, docsizes, ids = proc_docs(docs, stoplist, stat.fulltext)

    doc_ids = ids
    random.shuffle(doc_ids)

    if stat.method=="NM":
        tfidf = tfidf_vectorizer.fit_transform(abstracts)
        vectorizer = tfidf_vectorizer
    else:
        tfidf = count_vectorizer.fit_transform(abstracts)
        vectorizer = count_vectorizer

    for k in range(k_folds):
        train_set = [i for i,x in enumerate(doc_ids) if i % k_folds !=k]
        test_set = [i for i,x in enumerate(doc_ids) if i % k_folds ==k]

        X_train = tfidf[train_set,]
        X_test = tfidf[test_set,]

        if stat.method=="NM":
            model = NMF(
                n_components=K, random_state=1,
                alpha_W=alpha, alpha_H=alpha, l1_ratio=.1, verbose=False,
                init='nndsvd', max_iter=n_samples
            ).fit(X_train)
            w_test = model.transform(X_test)
            rec_error = _beta_divergence(
                X_test,
                w_test,
                model.components_,
                'frobenius',
                square_root=True
            )

        else:
            model = LDA(
                n_components=K,
                doc_topic_prior=stat.alpha,
                max_iter=stat.max_iter,
                n_jobs=6
            ).fit(X_test)
            w_test = model.transform(X_test)
            rec_error = _beta_divergence(
                X_test,
                w_test,
                model.components_,
                'frobenius',
                square_root=True
            )
        kf, created = KFold.objects.get_or_create(
            model=stat,
            K=k
        )
        kf.error = rec_error
        kf.save()

    return

@shared_task
def do_nmf(run_id, no_processes=16):
    stat = RunStats.objects.get(run_id=run_id)
    qid = stat.query.id
    K = stat.K

    TopicTerm.objects.filter(run_id=run_id).delete()
    DocTopic.objects.filter(run_id=run_id).delete()
    Topic.objects.filter(run_id=run_id).delete()

    stat.term_set.clear()

    alpha = stat.alpha
    n_features = stat.max_features
    if n_features == 0:
        n_features = 100000000000
    limit = stat.limit
    ng = stat.ngram

    # if stat.method=="LD" and stat.lda_library!=RunStats.WARP:
    #     if stat.max_iter == 200:
    #         stat.max_iter = 10
    #     if stat.max_iter > 100:
    #         stat.max_iter = 90

    n_samples = stat.max_iter


    stat.process_id = os.getpid()
    stat.status = 1
    stat.save()

    if stat.fulltext:
        docs = Doc.objects.filter(query=qid,fulltext__iregex='\w')
    else:
        docs = Doc.objects.filter(query=qid,content__iregex='\w')

    # if we are limiting, probably for testing, then do that
    if limit > 0:
        docs = docs[:limit]

    print('\n###############################\
    \n## Topic modeling (method: {}, library: {}) on query {} with {} documents \
and {} topics (run_id: {})\n'.format(stat.method, stat.lda_library,
                                     qid, docs.count(),K, run_id))

    # Get the docs into lists
    abstracts, docsizes, ids, citations = proc_docs(docs, stoplist, stat.fulltext, stat.citations)

    scaled_citations = 1 + RobustScaler(with_centering=False).fit_transform(np.array(citations).reshape(-1,1))

    sentences = [get_sentence(x) for x in abstracts]
    w2v = gensim.models.Word2Vec(sentences)
    validation_measure = WithinTopicMeasure(
        ModelSimilarity(w2v)
    )

    if stat.fancy_tokenization:
        ######################################
        ## A fancy tokenizer

        from nltk import wordpunct_tokenize
        from nltk import WordNetLemmatizer
        from nltk import sent_tokenize
        from nltk import pos_tag
        from nltk.corpus import stopwords as sw
        punct = set(string.punctuation)
        from nltk.corpus import wordnet as wn
        stopwords = set(sw.words('english'))

        if stat.extra_stopwords:
            stopwords = stopwords | set(stat.extra_stopwords)

        def lemmatize(token, tag):
                tag = {
                    'N': wn.NOUN,
                    'V': wn.VERB,
                    'R': wn.ADV,
                    'J': wn.ADJ
                }.get(tag[0], wn.NOUN)
                return WordNetLemmatizer().lemmatize(token, tag)

        kws = Doc.objects.filter(
            query=stat.query,
            kw__text__iregex='\w+[\-\ ]'
        ).values('kw__text').annotate(
            n = Count('pk')
        ).filter(n__gt=len(abstracts)//200).order_by('-n')

        kw_text = set([x['kw__text'].replace('-',' ') for x in kws])
        kw_ws = set([x['kw__text'].replace('-',' ').split()[0] for x in kws]) - stopwords

        def fancy_tokenize(X):

            common_words = set([x.lower() for x in X.split()]) & kw_ws
            for w in list(common_words):
                w = w.replace('(','').replace(')','')
                wpat = "({}\W*\w*)".format(w)
                wn = [x.lower().replace('-',' ') for x in re.findall(wpat, X, re.IGNORECASE)]
                kw_matches = set(wn) & kw_text
                if len(kw_matches) > 0:
                    for m in kw_matches:
                        insensitive_m = re.compile(m, re.IGNORECASE)
                        X = insensitive_m.sub(' ', X)
                        yield m.replace(" ","-")

            for sent in sent_tokenize(X):
                for token, tag in pos_tag(wordpunct_tokenize(sent)):
                    token = token.lower().strip()
                    if token in stopwords:
                        continue
                    if all(char in punct for char in token):
                        continue
                    if len(token) < 3:
                        continue
                    if all(char in string.digits for char in token):
                        continue
                    lemma = lemmatize(token,tag)
                    yield lemma

        tokenizer = fancy_tokenize
    else:
        tokenizer = snowball_stemmer()


    #######################################

    #############################################
    # Use tf-idf features for NMF.
    print("Extracting tf-idf features ...")
    tfidf_vectorizer = TfidfVectorizer(
        max_df=stat.max_df,
        min_df=stat.min_freq,
        max_features=n_features,
        ngram_range=(ng,ng),
        tokenizer=tokenizer,
        stop_words=list(stoplist)
    )

    count_vectorizer = CountVectorizer(
        max_df=stat.max_df,
        min_df=stat.min_freq,
        max_features=n_features,
        ngram_range=(ng,ng),
        tokenizer=tokenizer,
        stop_words=list(stoplist)
    )

    t0 = time()
    if stat.method=="NM":
        tfidf = tfidf_vectorizer.fit_transform(abstracts)
        vectorizer = tfidf_vectorizer
    else:
        tfidf = count_vectorizer.fit_transform(abstracts)
        vectorizer = count_vectorizer
    print("done in %0.3fs." % (time() - t0))
    stat.tfidf_time = time() - t0
    stat.save()

    print(tfidf)
    print(tfidf.todense())
    if citations is not False:
        tfidf = tfidf.multiply(scaled_citations)

    del abstracts
    gc.collect()

    if stat.db:
        vocab = vectorizer.get_feature_names_out()
        vocab_ids = []
        print("Using billiard instead of pool")
        pool = Pool(processes=no_processes)
        vocab_ids.append(pool.map(partial(add_features, run_id=run_id),vocab))
        pool.terminate()
        #del vocab
        vocab_ids = vocab_ids[0]

        ## Make some topics
        django.db.connections.close_all()
        topic_ids = db.add_topics(K, run_id)
        gc.collect()

    # Fit the NMF model
    print("Fitting the model with tf-idf features, "
          "n_samples=%d and n_features=%d..."
          % (n_samples, n_features))
    t0 = time()
    if stat.method=="NM":
        model = NMF(
            n_components=K, random_state=1,
            alpha_W=alpha, alpha_H=alpha, l1_ratio=.1, verbose=True,
            init='nndsvd', max_iter=n_samples
        )
        dtm = csr_matrix(model.fit_transform(tfidf))
        components = csr_matrix(model.components_)
    else:
        if stat.lda_library == RunStats.LDA_LIB:
            model = lda.LDA(
                n_topics=K,
                alpha=stat.alpha,
                eta=stat.alpha,
                n_iter=stat.max_iter*10,
            ).fit(tfidf)
            dtm = model.doc_topic_
            components = csr_matrix(model.components_)
        elif stat.lda_library == RunStats.WARP:
            # Export warp lda
            try:
                warp_path = settings.WARP_LDA_PATH
                os.chdir(warp_path)
            except:
                print("warplda is not installed, or its path is not defined in settings, exiting....")
                return
            fname = wpu.export_warp_lda(ids, tfidf, vocab, run_id)
            # preformat
            os.system(f'./format -input {fname} -prefix {run_id} train')
            # Run warp lda
            runcmd = f'./warplda --prefix {run_id} --k {stat.K}'
            if stat.alpha:
                runcmd += f' -alpha {stat.alpha}'
            if stat.beta:
                runcmd += f' -beta {stat.beta}'
            else:
                stat.beta = 0.01 # default beta value
                stat.save()
            if stat.max_iter:
                runcmd += f' --niter {stat.max_iter}'
            runcmd += ' train.model'
            print("Running warplda.")
            os.system(runcmd)
            print("Finished running warplda, importing results.")

            warp_vocab = np.loadtxt(f'{run_id}.vocab',dtype=str)
            warp_translate = np.argsort(warp_vocab).argsort()
            # Import warp lda as matrices
            with open(f'{run_id}.model', 'r') as f:
                for i, l in enumerate(f):
                    if i==0:
                        M = int(l.split()[0])
                        N = int(l.split()[1])
                        components = lil_matrix((N,M))
                    else:
                        largs = l.split('\t')[1].strip().split()
                        for la in largs:
                            wid = warp_translate[i-1]
                            t,n = la.split(':')
                            components[int(t),wid] = int(n)

            components = components.todense()
            for k in range(components.shape[0]):
                components[k,:] = (components[k,:] + stat.beta) / (components[k,:].sum() + stat.K*stat.beta)
            components = csr_matrix(components)

            dtm = lil_matrix((len(ids),N))
            with open(f'{run_id}.z.estimate', 'r') as f:
                for i, l in enumerate(f):
                    largs = l.split(' ',maxsplit=1)[1].strip().split()
                    for la in largs:
                        w,t = la.split(':')
                        dtm[i,int(t)] += 1

            theta = dtm.todense()
            for i in range(dtm.shape[0]):
                theta[i,:] = (theta[i,:] + stat.alpha) / (theta[i,:].sum() + stat.K*stat.alpha)

            dtm = csr_matrix(theta)



        else:
            model = LDA(
                n_components=K,
                doc_topic_prior=stat.alpha,
                topic_word_prior=stat.beta,
                learning_method=stat.get_lda_learning_method_display().lower(),
                max_iter=stat.max_iter,
                n_jobs=2
            ).fit(tfidf)

            dtm = csr_matrix(model.transform(tfidf))
            components = csr_matrix(model.components_)

    print("done in %0.3fs." % (time() - t0))
    stat.nmf_time = time() - t0

    if stat.db:
        ## Add topics terms
        print("Adding topicterms to db")
        t0 = time()
        ldalambda = find(components)
        topics = range(len(ldalambda[0]))
        tts = []
        pool = Pool(processes=no_processes)

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
        print("Adding DocTopics")
        gamma =  find(dtm)
        glength = len(gamma[0])

        chunk_size = 100000

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
            for p in range(no_processes):
                doc_batches.append([x for x in docs if x % no_processes == p])
            pool = Pool(processes=no_processes)
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
            print(make_t)
            django.db.connections.close_all()

            add_t0 = time()
            values_list = [item for sublist in values_list for item in sublist]
            pool = Pool(processes=no_processes)
            pool.map(insert_many, values_list)
            pool.terminate()
            add_t += time() - add_t0
            print(add_t)
            gc.collect()
            sys.stdout.flush()

        stat.db_time = stat.db_time + time() - t0
        print("done in %0.3fs." % (time() - t0))


    em = 0
    for i in range(K):
        if dtm[:,i].nnz == 0:
            em+=1

    stat.empty_topics = em
    if stat.method=="NM":
        stat.error = model.reconstruction_err_
        stat.errortype = "Frobenius"
    elif stat.method=="LD":
        if stat.lda_library == RunStats.LDA_LIB:
            stat.error = model.loglikelihood()
            stat.errortype = "Log likelihood"
            stat.iterations = model.n_iter
        elif stat.lda_library == RunStats.WARP:
            pass
        else:
            stat.error = model.perplexity(tfidf)
            stat.errortype = "Perplexity"
            stat.iterations = model.n_iter_
    stat.last_update=timezone.now()

    if stat.db:
        term_rankings = []

        topics = Topic.objects.filter(
            run_id=run_id
        )

        for topic in topics:
            term_ranking = list(Term.objects.filter(
                topicterm__topic=topic
            ).order_by(
                '-topicterm__score'
            ).values_list('title',flat=True)[:50])
            term_rankings.append(term_ranking)

        stat.coherence = validation_measure.evaluate_rankings(
            term_rankings
        )
        stat.save()
        if stat.db:
            management.call_command('update_run',run_id)

    stat.status=3

    stat.save()
