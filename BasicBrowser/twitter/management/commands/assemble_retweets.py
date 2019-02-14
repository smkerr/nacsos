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

class Command(BaseCommand):
    help = 'redoes searches'

    def handle(self, *args, **options):
        rts = Status.objects.filter(
            text__regex="^RT @",
            retweeted_status__isnull=True
        )
        print(rts.count())
        texts = rts.values_list('text',flat=True).distinct()
        for t in texts:
            # Get the statuses which have this same text
            trts = Status.objects.filter(text=t)
            # The original text is that which comes after the first colon
            otext = ":".join(t.split(':')[1:]).strip()
            try:
                ostatus = Status.objects.get(text=otext)
            except:
                continue
            ostatus.retweeted=True
            for s in trts:
                ostatus.retweeted_by.add(s.author)
                s.retweeted_status = ostatus
                s.save()
            ostatus.save()
