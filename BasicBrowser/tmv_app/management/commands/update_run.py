from django.core.management.base import BaseCommand, CommandError
from tmv_app.views import *
rfrom tmv_app.models import *

class Command(BaseCommand):
    help = 'update a run, do a load of calculations  \
    on it so that it loads quicker'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)

    def handle(self, *args, **options):
