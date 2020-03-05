from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import scoping.models as sms
import os
import sys
from datetime import datetime, timedelta
import django
from django.utils import timezone
import time
import tweepy
from django.conf import settings
import twitter.utils.utils as tutils
import psutil

class Command(BaseCommand):
    help = 'redoes searches with api'

    def handle(self, *args, **options):

        def lookup_statuses(api, slookup):
            tf = "%a %b %d %H:%M:%S %z %Y"
            tstatuses = api.statuses_lookup(slookup,tweet_mode="extended")
            print(len(tstatuses))
            for s in tstatuses:
                try:
                    tutils.parse_status(s)
                except:
                    print("Couldn't save this for some reason, exiting...")
                    print(s._json)
                    sys.exit()
            return

        pid = os.getpid()

        for p in psutil.process_iter():
            if "hydrate_tweets" in p.cmdline() and p.pid != pid:
                print("api getting is already running... skipping for today")
                return

        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_SECRET)
        api = tweepy.API(auth,wait_on_rate_limit=True)
        dots = sms.DocOwnership.objects.filter(
            tweet__isnull=False
        ).values_list('tweet__id',flat=True)
        dry_statuses = Status.objects.filter(
            pk__in=dots,
            text__icontains="…",
            api_got=False
        )
        if not dry_statuses.exists() or dry_statuses.count() < 200:
            dry_statuses = Status.objects.filter(
                api_got=False,
                #docownership__isnull=False,
                #tag__isnull=False,
                #text__icontains="…",
                #searches__project=197
                searches=57,
                #searches__project=224
            ).order_by('-fetched')
        print(dry_statuses.count())
        slookup = []
        for s in dry_statuses.iterator():
            slookup.append(s.id)
            if len(slookup) == 100:
                lookup_statuses(api, slookup)
                slookup = []
        if len(slookup) > 0:
            lookup_statuses(api, slookup)
