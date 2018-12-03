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
from pathlib import Path

class Command(BaseCommand):
    help = 'redoes searches'
    def add_arguments(self, parser):
        parser.add_argument('weeks', type=int)

    def handle(self, *args, **options):

        def parse_tjson(uname):
            if not Path("tweets/users.json").is_file():
                return
            with open("tweets/users.json") as f:
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
            if not Path("tweets/tweets.json").is_file():
                return
            with open("tweets/tweets.json") as f:
                for l in f:
                    tweet = json.loads(l)
                    try:
                        user, created = User.objects.get_or_create(
                            id=tweet['user_id']
                        )
                    except:
                        user, created = User.objects.get_or_create(
                            id=tweet['user_id'],
                            screen_name=tweet['username']
                        )
                    if tweet["username"]==uname.replace("@",""):
                        user.fetched = timezone.now()
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


        now = datetime.now() + timedelta(days=1)
        for i in list(range(options['weeks']))[::-1]:
            now = now - timedelta(days=7*i)
            then = now - timedelta(days=8)
            print(now.strftime("%Y-%m-%d"))
            print(then.strftime("%Y-%m-%d"))
            for u in User.objects.filter(monitoring=True):
                print(u.screen_name)
                try:
                    os.remove("tweets/users.json")
                    os.remove("tweets/tweets.json")
                except:
                    pass
                c = twint.Config()
                c.Username = u.screen_name
                c.Profile_full = True
                c.Since = then.strftime("%Y-%m-%d")
                c.Until = now.strftime("%Y-%m-%d")
                c.Store_json = True
                c.All = u.screen_name
                c.Output = "tweets.json"
                twint.run.Profile(c)

                parse_tjson(u.screen_name)
                u.scrape_fetched=django.utils.timezone.make_aware(now)
                if u.since is None or u.since > django.utils.timezone.make_aware(then):
                    u.since = django.utils.timezone.make_aware(then)
                if u.until is None or u.until < django.utils.timezone.make_aware(now):
                    u.until = django.utils.timezone.make_aware(now)
                u.save()
