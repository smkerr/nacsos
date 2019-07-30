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

        docs = Doc.objects.filter(query=6187,authors__isnull=True)

        for d in docs:
            das = d.docauthinst_set.order_by('AU','position').distinct('AU').values_list('id',flat=True)
            unique = d.docauthinst_set.filter(id__in=das).order_by('position').values_list('AU',flat=True)
            d.authors = ", ".join(unique)
            fa = d.docauthinst_set.order_by('position').first()
            if fa is not None:
                d.first_author = fa.AU
            d.save()
