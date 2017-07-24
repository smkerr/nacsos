from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

import re, nltk
from nltk.stem import SnowballStemmer

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)

    def handle(self, *args, **options):
        qid = options['qid']
        q = Query.objects.get(pk=qid)

        st = SnowballStemmer("english")
        stoplist = set(nltk.corpus.stopwords.words("english"))
        Bigram.objects.all().delete()

        docs = Doc.objects.filter(query=q)
        docs = docs.filter(docbigram__isnull=True)
        n = docs.count()

        p = '(\w*?)(\W*?)(\w*)(\W*)([sS]ustainab[a-zA-Z]*)(\W*)(\w*)(\W*)(\w*)'

        i = 0
        for d in docs.iterator():
            if i % 10000 == 0:
                print("processing doc {}, of {}...".format(i,n))
            i+=1
            if d.content is not None:
                dmatches = re.findall(p, d.content)
            else:
                dmatches = []
            tmatches = re.findall(p,d.title)

            dmatches = dmatches + tmatches

            for m in dmatches:
                for pos in [-1,1]:
                    s = m[4+pos]
                    w2 = m[4+pos*2]
                    if not re.match('\S',s) and len(w2)>0:
                        if w2 in stoplist:
                            s = m[4+pos*3]
                            w2 = m[4+pos*4]

                        if not re.match('\S',s) and w2 not in stoplist and len(w2) > 0:

                            bg, created = Bigram.objects.get_or_create(
                                word1=m[4],
                                word2=w2,
                                pos=pos
                            )
                            if created:
                                s1 = st.stem(m[4])
                                s2 = st.stem(w2)
                                bg.stem1 = s1
                                bg.stem2 = s2
                                bg.save()
                            dbg, created = DocBigram.objects.get_or_create(
                                doc = d,
                                bigram = bg
                            )
                            dbg.save()
