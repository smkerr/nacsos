from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import os
import sys
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

        pid = os.getpid()

        for p in psutil.process_iter():
            if "get_retweets" in p.cmdline() and p.pid != pid:
                print("api getting is already running... skipping for today")
                return

        tweets = Status.objects.filter(
            retweets_count__gt=0,
            retweeted_by__isnull=True
        )[:10000]
        print("getting retweets:")
        print(f"{tweets.count()} remaining")
        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_SECRET)
        api = tweepy.API(auth,wait_on_rate_limit=True)
        for t in tweets.iterator():
            try:
                retweets = api.retweets(t.pk)
            except tweepy.TweepError as e:
                print(e)
                pass
            print(t)
            for r in retweets:
                s = tutils.parse_status(r)
                if s is not None:
                    s.api_got = False
                    s.retweeted_status = t
                    s.save()
                    t.retweeted_by.add(s.author)
                    t.save()
            time.sleep(1)
