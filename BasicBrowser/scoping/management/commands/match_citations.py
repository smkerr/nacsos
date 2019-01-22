from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from multiprocess import Pool
import re, nltk, django, gc, time
from nltk.stem import SnowballStemmer
from functools import partial


class Command(BaseCommand):
    help = 'try and match citations to documents'


    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)

    def handle(self, *args, **options):

        def citation_chunk(citations,qid):
            django.db.connections.close_all()
            docs = Doc.objects.all()
            #docs = Doc.objects.filter(query=qid)
            for c in citations.iterator():
                if c.doi is not None:
                    dmatches = docs.filter(wosarticle__di=c.doi)
                else:
                    fields = c.ftext.split(', ')
                    au = ", ".join(fields[0].split())
                    try:
                        au = re.findall("([\w\s]*)",au)[0]
                    except:
                        continue

                    try:
                        py = int(fields[1])
                    except:
                        py = None
                        continue
                    try:
                        so = JournalAbbrev.objects.get(abbrev=fields[2].strip())
                    except:
                        so = None

                    if py is not None:
                        #dmatches = docs.filter(docauthinst__AU__icontains=au,PY=py)
                        dmatches = docs.filter(docauthinst__AU=au,PY=py)
                    else:
                        dmatches = docs.filter(docauthinst__AU__icontains=au)

                    if so is not None:
                        dmatches = dmatches.filter(wosarticle__so__iexact=so.fulltext)

                dc = dmatches.count()
                c.docmatches = dc
                if dc==1:
                    c.referent = dmatches.first()

                c.save()

        ####################################
        ## Process the citations in parallel in chunks

        qid = options['qid']
        q = Query.objects.get(pk=qid)

        citations = Citation.objects.filter(docmatches__isnull=True)

        c_count = citations.count()

        chunk_size = 100000
        cores = 3

        for i in range(c_count//chunk_size+1):
            cdos = []


            f = i*chunk_size
            print(f)
            t0 = time.time()
            chunks = []
            minichunk_size = chunk_size//cores
            jb = 0
            for j in range(cores):
                jf = f+minichunk_size*j
                jl = f+minichunk_size*(j+1)
                if jl > c_count:
                    jl = c_count
                minichunk_docs = citations[jf:jl]
                chunks.append(minichunk_docs)
            pool = Pool(processes=cores)
            #pool.map(citation_chunk,chunks)
            pool.map(partial(citation_chunk,qid = qid),chunks)
            pool.terminate()
            gc.collect()
            t = time.time() - t0
            print("docs per second = {}".format(round(chunk_size/t,2)))
