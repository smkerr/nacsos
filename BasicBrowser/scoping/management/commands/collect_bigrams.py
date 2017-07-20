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

        docs = Doc.objects.filter(query=q,content__iregex='\w')
        n = docs.count()
        i = 0
        for d in docs.iterator():
            if i % 10000 == 0:
                print("processing doc {}, of {}...".format(i,n))
            i+=1
            dmatches = re.findall(
                '(\w*)(\W*)([sS]ustainab[a-zA-Z]*)(\W*)(\w*)',
                d.content
            )
            for m in dmatches:
                if not re.match('\S',m[1]) and m[0] not in stoplist and len(m[0]) > 0:

                    bg, created = Bigram.objects.get_or_create(
                        word1=m[2],
                        word2=m[0],
                        pos=-1
                    )
                    if created:
                        s1 = st.stem(m[2])
                        s2 = st.stem(m[0])
                        bg.stem1 = s1
                        bg.stem2 = s2
                        bg.save()
                    dbg, created = DocBigram.objects.get_or_create(
                        doc = d,
                        bigram = bg
                    )
                    dbg.save()

                if not re.match('\S',m[3]) and m[4] not in stoplist and len(m[4]) > 0:
                    bg, created = Bigram.objects.get_or_create(
                        word1=m[2],
                        word2=m[4],
                        pos=1
                    )
                    if created:
                        s1 = st.stem(m[2])
                        s2 = st.stem(m[4])
                        bg.stem1 = s1
                        bg.stem2 = s2
                        bg.save()
                    dbg, created = DocBigram.objects.get_or_create(
                        doc = d,
                        bigram = bg
                    )
                    dbg.save()
