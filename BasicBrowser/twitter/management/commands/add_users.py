from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import pandas as pd
import csv
import twint
import json
import os
from datetime import datetime
import django
from django.utils import timezone
import time
import os
import sys

class Command(BaseCommand):
    help = 'adds users from a csv file'
    def add_arguments(self, parser):
        parser.add_argument('fpath')


    def handle(self, *args, **options):

        def parse_tjson(uname):
            with open("twitter/users.json") as f:
                for l in f:
                    u = json.loads(l)
                    user, created = User.objects.get_or_create(
                        id=u['id']
                    )
                    if u["username"]==uname.replace("@",""):
                        user.fetched = timezone.now()
                        user.monitoring = True
                        user.save()
                    if created:
                        user.screen_name=u['username']
                        user.save()
                main_user = user
            with open("twitter/tweets.json") as f:
                for l in f:
                    tweet = json.loads(l)
                    user, created = User.objects.get_or_create(
                        id=tweet['user_id']
                    )
                    if tweet["username"]==uname.replace("@",""):
                        user.fetched = timezone.now()
                        user.monitoring = True
                        user.save()
                    if created:
                        user.screen_name=tweet['username']
                        user.save()
                    status, created = Status.objects.get_or_create(
                        id=tweet['id']
                    )
                    status.fetched = timezone.now()
                    status.save()
                    if created:
                        t = datetime.strptime(
                            "{} {}".format(tweet['date'],tweet['time']),
                            "%Y-%m-%d %H:%M:%S"
                            )
                        t = django.utils.timezone.make_aware(t)
                        status.author=user
                        status.created_at=t
                        status.favorites_count = tweet['likes_count']
                        status.retweets_count = tweet['retweets_count']
                        status.place = tweet['location']
                        status.text = tweet['tweet']
                        status.save()

                    if status.author != main_user:
                        status.retweeted_by.add(main_user)


        def get_tweets(uname):
            print(uname)
            try:
                os.remove("twitter/users.json")
                os.remove("twitter/tweets.json")
            except:
                pass
            out = sys.stdout

            f = open(os.devnull, 'w')
            sys.stdout = f

            c = twint.Config()
            c.Username = uname
            c.Store_json = True
            c.Output = "twitter.json"
            c.Retweets = True
            c.Profile_full = True
            c.All = uname
            twint.run.Profile(c)

            sys.stdout = out

            time.sleep(2)

            try:
                parse_tjson(uname)
            except:
                pass

        print(options['fpath'])
        with open(options['fpath']) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['handle'].lower()=="@EskenSaskia".lower():
                    print(row['handle'])
                    get_tweets(row['handle'])
