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

class Command(BaseCommand):
    help = 'redoes searches with api'

    def handle(self, *args, **options):

        def parse_statuses(statuses,ts):
            for s in statuses:
                tutils.parse_status(s,ts)

        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_SECRET)
        api = tweepy.API(auth,wait_on_rate_limit=True)

        for ts in TwitterSearch.objects.all():
            for d in range(1,15):
                then = datetime.now() - timedelta(days=d)
                then = django.utils.timezone.make_aware(then)
                forward = False
                results = True
                n_statuses = 0
                while results:
                    db_statuses = Status.objects.filter(
                        searches=ts,
                        api_got=True,
                        created_at__gt=then,
                        created_at__isnull=False
                    ).order_by('created_at')
                    first = db_statuses.first()
                    last = db_statuses.last()

                    if first is None:
                        statuses = api.search(
                            ts.string,
                            count=100,
                            result_type="recent",
                            tweet_mode="extended"
                        )
                    else:
                        print(first.created_at)
                        statuses = api.search(
                            ts.string,
                            max_id=first.id,
                            count=100,
                            result_type="recent",
                            tweet_mode="extended"
                        )
                    if len(statuses) == 0 or db_statuses.count()==n_statuses:
                        results=False
                    n_statuses = db_statuses.count()
                    print(f"parsing backward, returns {len(statuses)}")
                    parse_statuses(statuses, ts)

            results = True
            while results:
                statuses = Status.objects.filter(
                    searches=ts,
                    api_got=True,
                    created_at__gt=then,
                    created_at__isnull=False
                ).order_by('created_at')
                first = statuses.first()
                last = statuses.last()
                if last is None:
                    statuses = api.search(
                        ts.string,
                        count=100,result_type="recent",
                        tweet_mode="extended"
                    )
                else:
                    statuses = api.search(
                        ts.string, since_id=last.id,
                        count=100,result_type="recent",
                        tweet_mode="extended"
                    )
                if len(statuses) == 0:
                    results=False

                print(f"parsing forward ({forward}), returns {len(statuses)}")
                parse_statuses(statuses, ts)
