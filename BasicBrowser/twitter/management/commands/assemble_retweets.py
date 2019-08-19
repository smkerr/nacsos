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
import re
import random

class Command(BaseCommand):
    help = 'redoes searches'

    def add_arguments(self, parser):
        parser.add_argument('pid',type=int)

    def handle(self, *args, **options):

        pid = pk=options['pid']

        for search in TwitterSearch.objects.filter(project_id=pid):

            print(search.string)

            rts = search.status_set.filter(
                text__regex="^RT @",
                retweeted_status__isnull=True
            )#[:4000]
            rt_count = rts.count()
            print(rt_count)
            texts = list(set(rts.values_list('text',flat=True)))
            random.shuffle(texts)
            done_texts = []
            for i, t in enumerate(texts):
                if i % 100 == 0:
                    print(f"{i/rt_count:.2%}")
                if t in done_texts:
                    continue
                if  ":" not in t:
                    continue
                # Get the statuses which have this same text

                trts = search.status_set.filter(text=t)

                # The original text is that which comes after the first colon
                otext = ":".join(t.split(':')[1:]).strip()
                ltext = re.sub('(\S*…)','',otext).strip()
                try:
                    ostatus = Status.objects.get(text=otext)
                except:
                    try:
                        ostatus = Status.objects.get(text__startswith=ltext)
                    except:
                        continue
                done_texts.append(t)
                ostatus.retweeted=True
                for s in trts.iterator():
                    ostatus.retweeted_by.add(s.author)
                    s.retweeted_status = ostatus
                    s.save()
                ostatus.save()
