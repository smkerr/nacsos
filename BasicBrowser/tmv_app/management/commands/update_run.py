from django.core.management.base import BaseCommand, CommandError
from django.core import management
from tmv_app.views import *
from tmv_app.models import *

class Command(BaseCommand):
    help = 'update a run, do a load of calculations  \
    on it so that it loads quicker'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)

    def handle(self, *args, **options):
        run_id = options['run_id']
        stat = RunStats.objects.get(run_id=run_id)

        if stat.parent_run_id is not None:
            parent_run_id=stat.parent_run_id
        else:
            parent_run_id = run_id

        stat.topic_titles_current = False
        stat.topic_year_scores_current = False
        stat.topic_scores_current = False
        stat.docs_seen = DocTopic.objects.filter(
            run_id=parent_run_id
        ).values('doc_id').order_by().distinct().count()
        stat.save()

        if stat.method == "DT":
            update_dtopics(run_id)
            update_topic_titles(run_id)

            tops = Topic.objects.filter(run_id=parent_run_id)

            for t in tops:
                try:
                    tpt = TopicDTopic.objects.filter(
                        topic=t,
                        dynamictopic__run_id=run_id
                    ).order_by('-score').first().dynamictopic
                    t.primary_dtopic.add(tpt)
                    t.save()
                except:
                    pass

        elif stat.method == "BD":
            update_bdtopics(run_id)
        else:
            update_year_topic_scores(run_id)
            update_topic_scores(run_id)
            update_topic_titles(run_id)

            management.call_command('corr_topics',run_id)
