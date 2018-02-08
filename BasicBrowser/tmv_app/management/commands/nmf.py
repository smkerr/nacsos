from django.core.management.base import BaseCommand, CommandError
from tmv_app.models import *
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

class Command(BaseCommand):
    help = 'run a topic model'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)
        parser.add_argument('K',type=int)

        parser.add_argument('--alpha',type=float, default=0.01)
        parser.add_argument('--limit',type=int, default=0)
        parser.add_argument('--n_features',type=int, default=50000)
        parser.add_argument('--n_samples',type=int, default=1000)
        parser.add_argument('--ng',type=int, default=1)


    def handle(self, *args, **options):

        t00 = time()
        qid = options['qid']
        K = options['K']

        alpha = options['alpha']
        n_features = options['n_features']
        limit = options['limit']
        ng = options['ng']
        n_samples = options['n_samples']

        # Get the docs from the query
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
        tfidf_vectorizer = TfidfVectorizer(max_df=0.97, min_df=2,
                                           max_features=n_features,
                                           ngram_range=(ng,ng),
                                           tokenizer=snowball_stemmer(),
                                           stop_words=stoplist)
        t0 = time()
        tfidf = tfidf_vectorizer.fit_transform(abstracts)
        print("done in %0.3fs." % (time() - t0))

        del abstracts
        gc.collect()

        run_id = db.init(n_features)
        stat = RunStats.objects.get(run_id=run_id)
        stat.query = Query.objects.get(pk=qid)
        stat.method = "NM"
        stat.alpha = alpha
        stat.process_id = os.getpid()
        stat.save()

        # Get the vocab, add it to db
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
                  init='nndsvd', max_iter=500).fit(tfidf)

        print("done in %0.3fs." % (time() - t0))


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


        ## Add topic-docs
        gamma =  find(csr_matrix(nmf.transform(tfidf)))
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

        stat.error = nmf.reconstruction_err_
        stat.errortype = "Frobenius"
        stat.iterations = nmf.n_iter_
        stat.last_update=timezone.now()
        stat.save()
        management.call_command('update_run',run_id)



        totalTime = time() - t00

        tm = int(totalTime//60)
        ts = int(totalTime-(tm*60))

        print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
        print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
