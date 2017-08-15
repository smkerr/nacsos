from django.core.management.base import BaseCommand, CommandError
from tmv_app.models import *
import numpy as np
from sklearn.decomposition import NMF
from scipy.sparse import csr_matrix, find
from functools import partial
from multiprocess import Pool
from utils.db import *
from utils.utils import *
from scoping.models import *
from time import time
import gc, sys
from django.core import management


class Command(BaseCommand):
    help = 'rerun a dynamic topic model with a different number \
    or dynamic topics'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)
        parser.add_argument('K',type=int)

    def handle(self, *args, **options):
        parent_run_id = options['run_id']
        K = options['K']

        parent_stat = RunStats.objects.get(pk=parent_run_id)

        n_features = parent_stat.max_features

        run_id = init(n_features)
        stat = RunStats.objects.get(run_id=run_id)
        stat.query = Query.objects.get(pk=parent_stat.query.id)
        stat.method = "DT"
        stat.parent_run_id = parent_run_id
        stat.save()


        tops = Topic.objects.filter(run_id=parent_run_id)
        terms = Term.objects.all()

        B = np.zeros((tops.count(),terms.count()))

        wt = 0
        for topic in tops:
            tts = TopicTerm.objects.filter(
                topic=topic
            ).order_by('-score')[:50]
            for tt in tts:
                B[wt,tt.term.id] = tt.score
            wt+=1

        col_sum = np.sum(B,axis=0)
        vocab_ids = np.flatnonzero(col_sum)

        # we only want the columns where there are at least some
        # topic-term values
        B = B[:,vocab_ids]


        nmf = NMF(
            n_components=K, random_state=1,
            alpha=.1, l1_ratio=.5
        ).fit(B)


        ## Add dynamic topics
        dtopics = []
        for k in range(K):
            dtopic = DynamicTopic(
                run_id=RunStats.objects.get(pk=run_id)
            )
            dtopic.save()
            dtopics.append(dtopic)

        dtopic_ids = list(
            DynamicTopic.objects.filter(
                run_id=run_id
            ).values_list('id',flat=True)
        )

        print(dtopic_ids)

        ##################
        ## Add the dtopic*term matrix to the db
        print("Adding topicterms to db")
        t0 = time()
        ldalambda = find(csr_matrix(nmf.components_))
        topics = range(len(ldalambda[0]))
        tts = []
        pool = Pool(processes=8)
        tts.append(pool.map(partial(f_dlambda, m=ldalambda,
                        v_ids=vocab_ids,t_ids=dtopic_ids,run_id=run_id),topics))
        pool.terminate()
        tts = flatten(tts)
        gc.collect()
        sys.stdout.flush()
        django.db.connections.close_all()
        DynamicTopicTerm.objects.bulk_create(tts)
        print("done in %0.3fs." % (time() - t0))

        ## Add the wtopic*dtopic matrix to the database
        gamma = nmf.transform(B)

        for topic in range(len(gamma)):
            for dtopic in range(len(gamma[topic])):
                if gamma[topic][dtopic] > 0:
                    tdt = TopicDTopic(
                        topic = tops[topic],
                        dynamictopic_id = dtopic_ids[dtopic],
                        score = gamma[topic][dtopic]
                    )
                    tdt.save()

        ## Calculate the primary dtopic for each topic
        for t in tops:
            try:
                t.primary_dtopic = TopicDTopic.objects.filter(
                    topic=t
                ).order_by('-score').first().dynamictopic
                t.save()
            except:
                pass

        stat.error = parent_stat.error + nmf.reconstruction_err_
        stat.errortype = "Frobenius"
        stat.last_update=timezone.now()
        stat.save()
        print("updating and summarising run, {}".format(run_id))
        management.call_command('update_run',run_id)

        management.call_command('update_run',run_id)
