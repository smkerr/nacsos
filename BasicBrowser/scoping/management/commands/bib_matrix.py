from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

from multiprocess import Pool
from functools import partial
from scipy.sparse import coo_matrix, csr_matrix, find, tril
import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer
import networkx as nx

from utils.utils import *# flatten
from scoping.models import *

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)

    def handle(self, *args, **options):
        qid = options['qid']

        q = Query.objects.get(pk=qid)

        cdos = CDO.objects.filter(
            doc__query=q
        )[:2000000]

        doc_ids = set(cdos.values_list('doc__id',flat=True))

        mdocs = Doc.objects.filter(
            id__in=doc_ids
        )
        m = mdocs.count()

        # Create a dictionary mapping doc ids to row indices
        m_dict = dict(zip(
            list(mdocs.values_list('pk',flat=True)),
            list(range(m))
        ))
        # and its reverse
        rev_m_dict = dict(zip(
            list(range(m)),
            list(mdocs.values_list('pk',flat=True))
        ))

        del mdocs

        n = Citation.objects.count()
        # Create a dictionary mapping citation ids to column indices
        n_dict = dict(zip(
            list(Citation.objects.all().values_list('id',flat=True)),
            list(range(n))
        ))

        # Put a 1 in all the row column positions implied by the cdo objects
        print("ROWIDS")
        row_ids = list(cdos.values_list('doc__pk',flat=True))
        rows = np.array([m_dict[x] for x in row_ids])
        print("colids")
        col_ids = list(cdos.values_list('citation__id',flat=True))
        cols = np.array([n_dict[x] for x in col_ids])
        print("data")
        data = np.array([1]*cdos.count())
        print("matrix")
        Scoo = coo_matrix((data, (rows,cols)),shape=(m,n))

        # We don't need these anymore but they use a lot of memory
        del cdos
        del row_ids
        del rows
        del col_ids
        del cols
        del data
        del n_dict

        gc.collect()

        # Transform the document-citation matrix to sparse format
        S = Scoo.tocsr()
        del Scoo
        gc.collect()

        # Calculate the bibcouple matrix with nice matrix algebra (so fast!)
        print("transpose")
        St = S.transpose()
        print("multiply")
        Cmat = S*St

        del S
        del St
        gc.collect()

        # Create a network from the lower triangle of the bibcouple matrix
        ltri = tril(Cmat,k=-1)
        G = nx.from_scipy_sparse_matrix(ltri)

        nx.write_gpickle(G, f"/tmp/bibCouple_q_{qid}.pickle")
        with open(f"/tmp/docnet_dict_q_{qid}.pickle", "wb") as f:
            pickle.dump(m_dict, f)
        with open(f"/tmp/docnet_revdict_q_{qid}.pickle", "wb") as f:
            pickle.dump(rev_m_dict, f)
