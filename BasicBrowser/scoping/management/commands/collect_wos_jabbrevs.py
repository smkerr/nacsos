from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

import re, nltk
from nltk.stem import SnowballStemmer
from bs4 import BeautifulSoup
import requests
import sys
sys.setrecursionlimit(100000)

class Command(BaseCommand):
    help = 'try and match citations to documents'

    def handle(self, *args, **options):
        lstub = 'https://images.webofknowledge.com/images/help/WOS/'

        link = 'https://images.webofknowledge.com/images/help/WOS/Q_abrvjt.html'

        r = requests.get(link)
        soup = BeautifulSoup(r.content, 'html.parser')
        links = soup.find_all("a")

        JournalAbbrev.objects.all().delete()

        for l in links:
            try:
                letter = l["href"]
            except:
                continue

            llink = lstub+letter
            lr = requests.get(llink)
            lsoup = BeautifulSoup(lr.content, 'html.parser')

            #print(lr.content)
            s = lr.content.decode('utf-8')
            lines = s.split('\n')

            titles = [x for x in lines if "<DT>" in x]
            abbrevs = [x for x in lines if "<DD>" in x]

            print(len(titles))
            print(len(abbrevs))

            print(l)

            if len(titles) != len(abbrevs):
                print("ERROR, unequal line lengths")
                break
            for i in range(len(titles)):
                title = re.sub('<[^>]*>', '', titles[i]).strip()
                abbrev = re.sub('<[^>]*>', '', abbrevs[i]).strip()
                jabbrev, created = JournalAbbrev.objects.get_or_create(
                    fulltext=title
                )
                jabbrev.abbrev=abbrev
                try:
                    jabbrev.save()
                except:
                    pass
