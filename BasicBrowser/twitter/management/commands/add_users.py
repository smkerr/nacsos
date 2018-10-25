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

class Command(BaseCommand):
    help = 'adds users from a csv file'
    def add_arguments(self, parser):
        parser.add_argument('fpath')


    def handle(self, *args, **options):

        def parse_tjson(uname):
            with open("twitter.json") as f:
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
                        status.favourites_count = tweet['likes']
                        status.retweets_count = tweet['retweets']
                        status.place = tweet['location']
                        status.text = tweet['tweet']
                        status.save()

                    if tweet['username'] != tweet['user_rt'].replace("@",""):
                        try:
                            retweeter = User.objects.get(
                                screen_name=tweet['user_rt'].replace("@","")
                            )
                            status.retweeted_by.add(retweeter)
                        except:
                            print("arg")
                            pass

        def get_tweets(uname):
            try:
                os.remove("twitter.json")
            except:
                pass
            c = twint.Config()
            c.Username = uname
            c.Store_json = True
            c.Output = "twitter.json"
            c.All = uname
            twint.run.Profile(c)

            time.sleep(2)

            try:
                parse_tjson(uname)
            except:
                pass

        print(options['fpath'])
        with open(options['fpath']) as f:
            reader = csv.DictReader(f)
            for row in reader:
                get_tweets(row['handle'])
