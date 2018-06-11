from django.core.management.base import BaseCommand, CommandError
import os
from utils.utils import *

class Command(BaseCommand):
    help = 'collect bigrams from a query'

    def handle(self, *args, **options):
        media = settings.MEDIA_ROOT
        for f in os.listdir(media):
            dfs = DocFile.objects.filter(file=f)
            if dfs.count()==0:
                print(f)
