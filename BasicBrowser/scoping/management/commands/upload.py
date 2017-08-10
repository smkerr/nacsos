from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from utils.utils import *
import os

class Command(BaseCommand):
    help = 'print a WoS type file'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)
        parser.add_argument('db', type=str)
        parser.add_argument('update',type=bool, default=False)

    def handle(self, *args, **options):
        qid = options['qid']
        db = options['db']
        update = options['update']

        q = Query.objects.get(pk=qid)

        print(q.title)

        title = str(q.id)

        with open("/queries/"+title+"/results.txt", encoding="utf-8") as res:
            r_count = read_wos(res, q, update)

        print(r_count)
        django.db.connections.close_all()
        #q.r_count = n_records
        #q.save()
