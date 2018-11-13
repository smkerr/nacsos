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
            forward = False
            results = True
            #for i in range(1,1501):
            while results:
                statuses = Status.objects.filter(
                    searches=ts,
                    api_got=True,
                    created_at__isnull=False
                ).order_by('created_at')
                first = statuses.first()
                last = statuses.last()
                if first is None:
                    statuses = api.search(ts.string, rpp=100)
                elif forward==False:
                    statuses = api.search(ts.string, max_id=first.id, rpp=100)
                else:
                    statuses = api.search(ts.string, since_id=last.id, rpp=100)
                if len(statuses) == 0:
                    if forward:
                        results=False
                    else:
                        forward=True
                        statuses = api.search(ts.string, since_id=last.id, rpp=100)

                print(f"parsing forward ({forward}), returns {len(statuses)}")
                parse_statuses(statuses, ts)
