from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from scoping.tasks import *
from utils.utils import *
import os

class Command(BaseCommand):
    help = 'print a WoS type file'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)
        parser.add_argument('update',type=bool, default=False)
        parser.add_argument('celery', type=int, default=0)

    def handle(self, *args, **options):
        qid = options['qid']
        update = options['update']
        celery = options['celery']

        if celery == 1:
            upload_docs.delay(qid,update)
        else:
            upload_docs(qid, update)
