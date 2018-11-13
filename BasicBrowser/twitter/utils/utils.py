from django.core.management.base import BaseCommand, CommandError
from twitter.models import *
import os
from datetime import datetime, timedelta
import django
from django.utils import timezone
import time
import tweepy
from django.conf import settings

def parse_status(s, ts=None):
    tf = "%a %b %d %H:%M:%S %z %Y"
    sdata = s._json
    udata = sdata['user']
    status, created = Status.objects.get_or_create(
        id=sdata['id']
    )
    try:
        user = User.objects.get(
            id = udata['id']
        )
    except:
        user, created = User.objects.get_or_create(
            id = udata['id'],
            screen_name = udata['screen_name']
        )
    for f in udata:
        if udata[f] != "none":
            try:
                if f=="created_at":
                    udata[f] = datetime.strptime(udata[f],tf)
                field = User._meta.get_field(f)
                setattr(user, f, udata[f])
            except:
                pass

    user.save()

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
                #print(f)
                pass
    status.author = user
    status.api_got = True
    status.fetched = timezone.now()
    if ts is not None:
        status.searches.add(ts)
    status.save()
