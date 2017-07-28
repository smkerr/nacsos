from django.core.management.base import BaseCommand, CommandError
from tmv_app.views import *
rfrom tmv_app.models import *

class Command(BaseCommand):
    help = 'update a run, do a load of calculations  \
    on it so that it loads quicker'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)

    def handle(self, *args, **options):
        stat = RunStats.objects.filter(run_id=run_id)
        stat.topic_titles_current = False
        stat.topic_year_scores_current = False
        stat.topic_scores_current = False
        stat.docs_seen = DocTopic.objects.filter(run_id=run_id).values('doc_id').order_by().distinct().count()
        stat.save()

        if stat.method == "DT":
            update_dtopics(run_id)
        else if stat.method == "BD":
            update_bdtopics(run_id)
        else:
            update_year_topic_scores(run_id)        
            update_topic_scores(run_id)
            update_topic_titles(run_id)
