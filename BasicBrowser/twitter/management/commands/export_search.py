from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers import serialize
import pandas as pd
import csv
import twint
import json
import os
import sys
from datetime import datetime, timedelta
import django
from django.utils import timezone
import time
from pathlib import Path
import re
import random

class Command(BaseCommand):
    help = 'exports a set of tweets from a search id'

    def add_arguments(self, parser):
        parser.add_argument('sid',type=int)

    def handle(self, *args, **options):
        sid = pk=options['sid']

        search = TwitterSearch.objects.get(pk=sid)

        tweets = Status.objects.filter(searches=search)

        uids = set(tweets.values_list('author__id',flat=True))

        users = User.objects.filter(pk__in=uids)


        with open(f'{search.string}_tweets.json','w') as f:
            json.dump(serialize('json',tweets,cls=DjangoJSONEncoder),f)
        with open(f'{search.string}_users.json','w') as f:
            json.dump(serialize('json',users,cls=DjangoJSONEncoder),f)
