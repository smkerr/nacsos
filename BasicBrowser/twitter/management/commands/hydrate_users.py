from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import pandas as pd
import csv
import tweepy
import json
import os
from datetime import datetime
import django
from django.utils import timezone
import time
from django.conf import settings

class Command(BaseCommand):
    help = 'hydrates users with the twitter api'

    def handle(self, *args, **options):

        def lookup_users(api,ulookup):
            tf = "%a %b %d %H:%M:%S %z %Y"
            tusers = api.lookup_users(user_ids=ulookup)
            for u in tusers:
                udata = u._json
                user = User.objects.get(id=udata['id'])
                for f in udata:
                    if udata[f] != "none":
                        try:
                            if f=="created_at":
                                udata[f] = datetime.strptime(udata[f],tf)
                            field = User._meta.get_field(f)
                            setattr(user, f, udata[f])
                        except:
                            print(f)
                            pass
                user.fetched = timezone.now()
                user.save()
                for p in range(0,160):
                    try:
                        statuses = api.user_timeline(u.screen_name)
                        for s in statuses:
                            status, created = Status.objects.get_or_create(
                                id=s.id
                            )
                            sdata = s._json
                            for f in sdata:
                                if sdata[f] != "none":
                                    try:
                                        if f=="in_reply_to_user_id":
                                            new_user, created = User.objects.get_or_create(
                                                id=sdata[f]
                                            )
                                        if f=="in_reply_to_status_id":
                                            ns, created = Status.objects.get_or_create(
                                                id=sdata[f]
                                            )
                                        if f=="created_at":
                                            sdata[f] = datetime.strptime(sdata[f],tf)
                                        field = Status._meta.get_field(f)
                                        setattr(status, f, sdata[f])
                                    except:
                                        pass
                            status.author = user
                            status.api_got = True
                            status.fetched = timezone.now()
                            status.save()
                    except:
                        print(f"couldn't get the user {user} timeline")





        auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_SECRET)
        api = tweepy.API(auth,wait_on_rate_limit=True)
        users = User.objects.filter(monitoring=True).order_by('fetched')
        ulookup = []
        for u in users:
            ulookup.append(u.id)
            if len(ulookup)==100:
                lookup_users(api,ulookup)
                ulookup = []
        if len(ulookup) > 0:
            lookup_users(api,ulookup)
