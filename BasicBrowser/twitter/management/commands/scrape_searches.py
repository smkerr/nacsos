from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
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

class Command(BaseCommand):
    help = 'redoes searches'
    def add_arguments(self, parser):
        parser.add_argument('weeks', type=int)

    def handle(self, *args, **options):

        def parse_tjson(tsearch,fname):
            with open(fname) as f:
                for l in f:
                    tweet = json.loads(l)
                    try:
                        user, created = User.objects.get_or_create(
                            id=tweet['user_id']
                        )
                    except:
                        print(tweet)
                        sys.exit()
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


        prog, created = SearchProgress.objects.get_or_create(server="apsis")
        if prog.search_date is None:
            now = datetime.now() #- timedelta(days=77)
        else:
            now = prog.search_date
        for i in range(options['weeks']):
            now = now - timedelta(days=7)
            then = now - timedelta(days=8)
            print(now.strftime("%Y-%m-%d"))
            print(then.strftime("%Y-%m-%d"))
            try:
                prog.search_date = django.utils.timezone.make_aware(now)
            except:
                prog.search_date = now
            prog.save()
            for ts in TwitterSearch.objects.all().order_by('id'):
                try:
                    os.remove("tweets/tweets.json")
                except:
                    pass
                folder = f"tweets/tweets_{ts.string}_{now.strftime('%Y-%m-%d')}"
                fname = f"{folder}/tweets.json"
                c = twint.Config()
                c.Search = ts.string
                c.Since = then.strftime("%Y-%m-%d")
                c.Until = now.strftime("%Y-%m-%d")
                c.Store_json = True
                c.Output = folder
                twint.run.Search(c)

                path = Path(fname)

                if path.exists():
                    parse_tjson(ts,fname)
                    try:
                        os.remove(fname)
                        os.rmdir(folder)
                    except:
                        pass

                try:
                    then = django.utils.timezone.make_aware(now)
                except:
                    then = then

                ts.scrape_fetched=now
                if ts.since is None or ts.since > then:
                    ts.since = then
                if ts.until is None or ts.until < now:
                    ts.until = now
                ts.save()
