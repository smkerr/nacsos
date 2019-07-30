from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer

from utils.utils import *# flatten

class Command(BaseCommand):
    help = 'remove duplicates interactively'
    def add_arguments(self, parser):
        parser.add_argument('pid',type=int)

    def handle(self, *args, **options):
        pid=options['pid']

        notes = Note.objects.filter(effect__project_id=pid)
        for n in notes:
            dups = notes.exclude(id=n.id).filter(
                effect=n.effect,
                field_group=n.field_group,
                date__lt=n.date
            )
            if dups:
                print('\n\n########')
                print(dups.count())
                print(dups)
                print('## LATEST NOTE ##')

                print(n)

                dups.delete()
