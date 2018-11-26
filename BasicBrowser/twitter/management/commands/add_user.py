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
import twitter.models as tm
import tweepy
from parliament.models import *

from django.db.models import Count
from django.db.models.fields import DateField
from django.db.models.functions import Cast
from django.conf import settings

class Command(BaseCommand):
    help = 'adds users from a csv file'
    def add_arguments(self, parser):
        parser.add_argument('screen_name')

    def handle(self, *args, **options):
        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_SECRET)
        api = tweepy.API(auth,wait_on_rate_limit=True)

        u = api.get_user(screen_name=options['screen_name'])
        udata = u._json
        try:
            tuser = tm.User.objects.get(
                id = udata['id']
            )
            print(f"found user {tuser}")
        except:
            tuser, created = tm.User.objects.get_or_create(
                id = udata['id'],
                screen_name = udata['screen_name'].replace('@','')
            )
            print(f"created user {tuser}")

        tuser.monitoring = True
        tuser.save()
