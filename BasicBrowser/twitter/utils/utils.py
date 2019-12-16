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
    if "full_text" in sdata:
        sdata["text"] = sdata["full_text"]
    try:
        user = User.objects.get(
            id = udata['id']
        )
    except:
        try:
            user, created = User.objects.get_or_create(
                id = udata['id'],
                screen_name = udata['screen_name']
            )
        except:
            print("WARNING! Could not save user:")
            print(udata)
            return
    for f in udata:
        if udata[f] != "none":
            try:
                if f=="created_at":
                    udata[f] = datetime.strptime(udata[f],tf)
                field = User._meta.get_field(f)
                setattr(user, f, udata[f])
            except:
                pass

    try:
        user.save()
    except:
        print("WARNING! Could not save user:")
        print(udata)
        return

    for f in sdata:
        if sdata[f] != "none" and sdata[f] is not None:
            try:
                if f=="in_reply_to_user_id":
                    new_user, created = User.objects.get_or_create(
                        id=sdata[f]
                    )
                    status.in_reply_to_user = new_user
                elif f=="in_reply_to_status_id":
                    ns, created = Status.objects.get_or_create(
                        id=sdata[f]
                    )
                    status.in_reply_to_status = ns
                else:
                    if f=="created_at":
                        sdata[f] = datetime.strptime(sdata[f],tf)
                    if f=="retweet_count":
                        field = Status._meta.get_field("retweets_count")
                    elif f=="favorite_count":
                        field = Status._meta.get_field("favorites_count")
                    elif f=="full_text":
                        field = Status._meta.get_field("text")
                    else:
                        field = Status._meta.get_field(f)
                    setattr(status, field.name, sdata[f])
            except:
                pass
    status.author = user
    status.api_got = True
    status.fetched = timezone.now()
    if ts is not None:
        status.searches.add(ts)
    status.save()
    return status
