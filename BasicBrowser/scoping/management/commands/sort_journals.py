from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer
import time

from utils.utils import *# flatten
from bs4 import BeautifulSoup
import requests


class Command(BaseCommand):
    help = 'get journals'

    def handle(self, *args, **options):
        if JournalAbbrev.objects.count() < 1:
            link = 'https://images.webofknowledge.com/images/help/WOS/0-9_abrvjt.html'
            r = requests.get(link)
            bigsoup = BeautifulSoup(r.text,'html.parser')
            for link in bigsoup.find_all('a'):
                time.sleep(4)
                href = link.get('href')
                flink = 'https://images.webofknowledge.com/images/help/WOS/'+href
                r = requests.get(flink)
                soup = BeautifulSoup(r.text,'html.parser')
                titles = soup.find_all('dt')
                abbrevs = soup.find_all('dd')
                print('{}: {} titles, {} abbrevs'.format(href.split('_')[0],len(titles),len(abbrevs)))
                if 'Z' in href:
                    break
        docs = Doc.objects.filter(journal__isnull=True,UT__UT__contains="WOS:").order_by('id')
        #docs = Doc.objects.filter(UT__UT__contains="WOS:").order_by('id')
        abbrevs = 0
        fulls = 0
        nmatches = 0
        for d in docs.iterator():
            if hasattr(d, 'wosarticle'):
                so = d.wosarticle.so
            else:
                continue
            if so is None:
                continue
            try:
                j = JournalAbbrev.objects.get(fulltext__iexact=so)
                d.journal=j
                d.save()
                fulls+=1
            except:
                try:
                    j = JournalAbbrev.objects.get(abbrev__iexact=so)
                    d.journal=j
                    d.save()
                    abbrevs+=1
                except:
                    nmatches +=1
                    print(JournalAbbrev.objects.filter(fulltext__iexact=so).count())
                    print(so)

        print("fulls: {}\nabbrevs: {}\nnones: {}".format(fulls,abbrevs,nmatches))
            #break
