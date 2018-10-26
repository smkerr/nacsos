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
        parser.add_argument('string')


    def handle(self, *args, **options):

        def parse_tjson(tsearch):
            with open("twitter.json") as f:
                for l in f:
                    tweet = json.loads(l)
                    user, created = User.objects.get_or_create(
                        id=tweet['user_id']
                    )
                    if created:
                        user.screen_name=tweet['username']
                        user.save()
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
                        status.favourites_count = tweet['likes']
                        status.retweets_count = tweet['retweets']
                        status.place = tweet['location']
                        status.text = tweet['tweet']
                        status.save()

        string = options["string"]
        tsearch, created = TwitterSearch.objects.get_or_create(
            string=string
        )
        now = timezone.now()
        try:
            os.remove("twitter.json")
        except:
            pass
        c = twint.Config()
        c.Search = string
        c.Store_json = True
        c.Output = "twitter.json"
        twint.run.Search(c)

        parse_tjson(tsearch)
        tsearch.scrape_fetched=now
        tsearch.save()
