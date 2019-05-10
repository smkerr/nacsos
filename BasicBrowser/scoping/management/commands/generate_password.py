from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
import random
import re, nltk
from nltk.stem import SnowballStemmer
from bs4 import BeautifulSoup
import requests
import sys
sys.setrecursionlimit(100000)
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from django.db.models import Max, Min

class Command(BaseCommand):
    help = 'try and match citations to documents'

    def handle(self, *args, **options):
        DOC_SAMPLE = 500
        WORD_SAMPLE = 4000
        N_WORDS = 4

        def random_queryset_elements(qs, number):
            assert number <= 10000, 'too large'
            max_pk = qs.aggregate(Max('pk'))['pk__max']
            min_pk = qs.aggregate(Min('pk'))['pk__min']
            ids = set()
            while len(ids) < number:
                next_pk = random.randint(min_pk, max_pk)
                while next_pk in ids:
                    next_pk = random.randint(min_pk, max_pk)
                try:
                    found = qs.get(pk=next_pk)
                    ids.add(found.pk)
                    yield found
                except qs.model.DoesNotExist:
                    pass

        #docids = Doc.objects.filter(content__iregex="\w").values_list('id',flat=True)
        #sample = random.sample(list(docids),DOC_SAMPLE)
        #sdocs = Doc.objects.filter(id__in=sample)
        #sdocs = random_queryset_elements(Doc.objects.filter(content__iregex="\w"), DOC_SAMPLE)
        sdocs = random_queryset_elements(Doc.objects.all(), DOC_SAMPLE)
        #abstracts = [d.content for d in sdocs]
        abstracts = [d.content for d in sdocs if d.content is not None]
        r1 = ' [a-zA-Z]{5,10} '
        vec = CountVectorizer(token_pattern = r1)
        #vec = TfidfVectorizer(token_pattern = r1)
        tdf = vec.fit_transform(abstracts)
        sum_words = tdf.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
        words_freq =sorted(words_freq, key = lambda x: x[1], reverse=True)
        word_hoard = words_freq[:WORD_SAMPLE]
        pass_words = []
        for i in range(N_WORDS):
            w = random.sample(word_hoard,1)[0][0].strip()
            pass_words.append(w)

        password = "_".join(pass_words)
        return password
