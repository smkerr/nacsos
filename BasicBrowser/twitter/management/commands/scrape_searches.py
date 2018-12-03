from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import pandas as pd
import csv
import twint
import json
import os
from datetime import datetime, timedelta
import django
from django.utils import timezone
import time

class Command(BaseCommand):
    help = 'redoes searches'
    def add_arguments(self, parser):
        parser.add_argument('weeks', type=int)

    def handle(self, *args, **options):

        def parse_tjson(tsearch):
            with open("tweets/tweets.json") as f:
                for l in f:
                    tweet = json.loads(l)
                    user, created = User.objects.get_or_create(
                        id=tweet['user_id']
                    )
                    if created:
                        try:
                            user.screen_name=tweet['username']
                            user.save()
                        except:
                            print(tweet)
                            break
                    status, created = Status.objects.get_or_create(
                        id=tweet['id']
                    )
                    status.fetched = timezone.now()
                    status.save()
                    status.searches.add(tsearch)
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


        now = datetime.now() + timedelta(days=1)
        for i in range(options['weeks']):
            now = now - timedelta(days=7*i)
            then = now - timedelta(days=8)
            print(now.strftime("%Y-%m-%d"))
            print(then.strftime("%Y-%m-%d"))
            for ts in TwitterSearch.objects.all():
                try:
                    os.remove("tweets.json")
                except:
                    pass
                c = twint.Config()
                c.Search = ts.string
                c.Since = then.strftime("%Y-%m-%d")
                c.Until = now.strftime("%Y-%m-%d")
                c.Store_json = True
                c.Output = "tweets.json"
                twint.run.Search(c)

                parse_tjson(ts)
                ts.scrape_fetched=django.utils.timezone.make_aware(now)
                if ts.since is None or ts.since > django.utils.timezone.make_aware(then):
                    ts.since = django.utils.timezone.make_aware(then)
                if ts.until is None or ts.until < django.utils.timezone.make_aware(now):
                    ts.until = django.utils.timezone.make_aware(now)
                ts.save()
