from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import *
from utils.utils import *
import os

@shared_task
def do_search(s):
    s = Search.objects.get(pk=s)
    ps = Paragraph.objects.filter(text__iregex=s.text)
    Through = Paragraph.search_matches.through
    tms = [Through(paragraph=p,search=s) for p in ps]
    Through.objects.bulk_create(tms)
    s.par_count=ps.count()
    s.save()
    return tms
