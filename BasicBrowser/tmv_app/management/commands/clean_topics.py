from django.core.management.base import BaseCommand, CommandError
from tmv_app.models import *

import re, nltk
from nltk.stem import SnowballStemmer

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def add_arguments(self, parser):
        parser.add_argument('a',type=int)
        parser.add_argument('z',type=int)

    def handle(self, *args, **options):
        a = options['a']
        z = options['z']
        
        for s in RunStats.objects.filter(run_id__gte=a,run_id__lte=z).iterator():
            print(s)
            print(s.pk)
            Topic.objects.filter(run_id=s).delete()
            DocTopic.objects.filter(run_id=s.pk).delete()
            TopicTerm.objects.filter(run_id=s.pk).delete()
            s.delete()
