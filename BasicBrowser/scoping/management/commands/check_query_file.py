from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.db.models import Count
from scoping.models import *


class Command(BaseCommand):
    help = 'check a query file - how many records'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)

    def handle(self, *args, **options):
        qid = options['qid']
        q = Query.objects.get(pk=qid)
        p = 'TY  - '
        if q.query_file.name is not '':
            fpath = q.query_file.path
        else:
            if q.database=="scopus":
                fname = 's_results.txt'
            else:
                fname = 'results.txt'
            fpath = f'{settings.QUERY_DIR}/{qid}/{fname}'
            with open(fpath, 'r') as f:
                c = f.read().count(p)

        print('\n{} documents in downloaded file\n'.format(c))

        if q.doc_set.count() > 0:
            yts = q.doc_set.values('PY').annotate(
                n = Count('pk')
            )
            for y in yts:
                print('{} documents in {}'.format(y['n'],y['PY']))
