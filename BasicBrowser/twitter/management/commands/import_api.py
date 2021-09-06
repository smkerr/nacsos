

from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import django
from django.utils import timezone
import time
import tweepy
from django.conf import settings
import twitter.utils.utils as tutils
import re

class Command(BaseCommand):
    help = 'imports from api generated json'
    def add_arguments(self, parser):
        parser.add_argument('sid', type=int)
        parser.add_argument('prefix',type=str)


    def handle(self, *args, **options):
        ts = TwitterSearch.objects.get(pk=options['sid'])
        print(ts)

        directory = "/usr/local/apsis/tweets"

        for fname in os.listdir(directory):
            django.db.connection.close()
            if re.match(f"{options['prefix']}.*\.json",fname):
                print(fname)
                with open(directory+"/"+fname,"r") as f:
                    for line in f:
                        tweet = json.loads(line)
                        if 'users' in tweet:
                            for u in tweet['users']:
                                au, created = User.objects.get_or_create(
                                    id=u['id']
                                )
                                for key, value in u.items():
                                    if isinstance(value,str):
                                        value = value.replace("\x00", "\uFFFD")
                                    setattr(au, key, value)
                                au.save()
                            continue
                        if "newest_id" in tweet:
                            continue
                        t, created = Status.objects.get_or_create(id=tweet['id'])
                        t.api_got=True
                        for key, value in tweet.items():
                            au, created = User.objects.get_or_create(
                                id=tweet['author_id']
                            )
                            if "in_reply_to_user_id" in tweet:
                                au, created = User.objects.get_or_create(
                                    id=tweet['in_reply_to_user_id']
                                )
                            if isinstance(value,dict):
                                continue
                            else:
                                if isinstance(value,str):
                                    value = value.replace("\x00", "\uFFFD")
                                setattr(t,key, value)
                            if 'referenced_tweets' not in tweet:
                                continue
                            for rt in tweet['referenced_tweets']:
                                rto, created = Status.objects.get_or_create(id=rt['id'])
                                if rt['type']=="retweeted":
                                    t.retweeted_status_id=rt['id']
                                elif rt['type']=="replied_to":
                                    t.in_reply_to_status_id=rt['id']
                                else:
                                    pass
                                    # quote tweets, need to deal with this
                                    #print(tweet)
                                    #return
                        t.save()
                        t.searches.add(ts)
