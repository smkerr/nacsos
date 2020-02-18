
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
import shutil
import random
from django.contrib.postgres.aggregates.general import ArrayAgg
import gc

class Command(BaseCommand):
    help = 'exports a set of tweets from a search id'

    def add_arguments(self, parser):
        parser.add_argument('sid',type=int)

    def handle(self, *args, **options):
        sid = pk=options['sid']

        search = TwitterSearch.objects.get(pk=sid)

        tweets = Status.objects.filter(searches=search, retweeted_status__isnull=True)#.exclude(text__iregex="^RT @")

        uids = set(tweets.values_list('author__id',flat=True))

        users = User.objects.filter(pk__in=uids)

        n = tweets.count()

        print(f"{n} tweets, {len(uids)} users")

        exclude_fields = [
            'api_got','scrape_got','fetched', 'replies','retweets',
            'twitterbasemodel_ptr','searches','retweeted_by'
            ]
        fields = [x.name for x in Status._meta.get_fields() if x.name not in exclude_fields]
        fields.append('retweeted_by_user_id')

        if n < 1000000:

            tweets = tweets.filter(pk__in=tweets)
            tweet_values = tweets.prefetch_related('retweeted_by').annotate(
                retweeted_by_user_id=ArrayAgg('retweeted_by')
            ).values(*fields)
            with open(f'{search.string}_tweets.json','w') as f:
                #f.write(serialize('json',all_objects,cls=DjangoJSONEncoder,fields=fields))
                f.write(json.dumps(list(tweet_values),cls=DjangoJSONEncoder))
            with open(f'{search.string}_users.json','w') as f:
                f.write(serialize('json',users,cls=DjangoJSONEncoder))

        else:
            f = tweets.filter(created_at__isnull=False).order_by('created_at').first().created_at
            l = tweets.filter(created_at__isnull=False).order_by('created_at').last().created_at
            exporting = True
            i = 0
            try:
                os.mkdir(f"/usr/local/apsis/slowhome/galm/exports/{search.string}")
            except:
                shutil.rmtree(f"/usr/local/apsis/slowhome/galm/exports/{search.string}")
                os.mkdir(f"/usr/local/apsis/slowhome/galm/exports/{search.string}")
            while exporting:
                gc.collect()
                b = l - timedelta(days=30)
                t_ids = tweets.filter(created_at__gt=b,created_at__lte=l).exclude(text__iregex="^RT @").values_list('id',flat=True)
                t_chunk = tweets.filter(pk__in=t_ids)
                uids = set(t_chunk.values_list('author__id',flat=True))
                user_chunk = User.objects.filter(pk__in=uids)

                tweet_values = t_chunk.annotate(
                    retweeted_by_user_id=ArrayAgg('retweeted_by')
                ).values(*fields)

                with open(f'/usr/local/apsis/slowhome/galm/exports/{search.string}/{i}_tweets.json','w') as file:
                    #json.dump(serialize('json',tweets,cls=DjangoJSONEncoder),f)
                    file.write(json.dumps(list(tweet_values),cls=DjangoJSONEncoder))
                with open(f'/usr/local/apsis/slowhome/galm/exports/{search.string}/{i}_users.json','w') as file:
                    file.write(serialize('json',user_chunk,cls=DjangoJSONEncoder))

                l = l - timedelta(days=30)
                if b < f:
                    exporting = False

                i+=1
