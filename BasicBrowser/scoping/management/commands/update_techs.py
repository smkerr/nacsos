from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from scoping.tasks import *
from utils.utils import *
import os

class Command(BaseCommand):
    help = 'print a WoS type file'

    def handle(self, *args, **options):
        technologies = Technology.objects.all()

        for t in technologies:
            t.queries = t.query_set.count()
            tdocs = Doc.objects.filter(technology=t)
            itdocs = Doc.objects.filter(query__technology=t,query__type="default")
            tdocs = tdocs | itdocs
            t.docs = tdocs.distinct().count()
            t.nqs = t.queries
            t.ndocs = t.docs
            t.save()
