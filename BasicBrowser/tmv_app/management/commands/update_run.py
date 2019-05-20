from django.core.management.base import BaseCommand, CommandError
from django.core import management
from tmv_app.views import *
from tmv_app.models import *
from utils.tm_mgmt import *

class Command(BaseCommand):
    help = 'update a run, do a load of calculations  \
    on it so that it loads quicker'

    def add_arguments(self, parser):
        parser.add_argument('run_id',type=int)

    def handle(self, *args, **options):
        run_id = options['run_id']
        stat = RunStats.objects.get(run_id=run_id)

        print(run_id)
        print(stat)

        if stat.parent_run_id is not None:
            parent_run_id=stat.parent_run_id
        else:
            parent_run_id = run_id

        stat.topic_titles_current = False
        stat.topic_year_scores_current = False
        stat.topic_scores_current = False
        if stat.query:
            stat.docs_seen = DocTopic.objects.filter(
                run_id=parent_run_id
            ).values('doc_id').order_by().distinct().count()
        elif stat.psearch.search_object_type == 1:  # paragraphs
            stat.docs_seen = DocTopic.objects.filter(
                run_id=parent_run_id
            ).values('par_id').order_by().distinct().count()
        elif stat.psearch.search_object_type == 2:  # utterances
            stat.docs_seen = DocTopic.objects.filter(
                run_id=parent_run_id
            ).values('ut_id').order_by().distinct().count()
        else:
            print("Did not calculate number of docs/paragraphs/utterances")
        stat.save()

        if stat.method == "DT":
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
                    print("Could not assign dynamic topic to topic object")
                    pass

            update_topic_scores(parent_run_id)
            # fmh: not working, therefore disabled
            update_dtopics(run_id)

            pstat = RunStats.objects.get(run_id=parent_run_id)
            pstat.topic_titles_current = False
            pstat.save()
            update_topic_titles(run_id)

            yearly_topic_term_scores(run_id)
            #management.call_command('corr_topics',run_id)
            if stat.query:
                if stat.query.project.id == 23:
                    update_ipcc_coverage(run_id)
            normalise_tdts(run_id)

        elif stat.method == "BD":
            update_bdtopics(run_id)
        else:
            try:
                update_bdtopics(run_id)
            except:
                pass
            management.call_command('corr_topics',run_id)
            topicterm_lscores(run_id)
            update_year_topic_scores(run_id)
            update_topic_scores(run_id)
            update_topic_titles(run_id)
            update_ar_scores(run_id)
            if stat.query:
                if stat.query.project.id == 23:
                    update_ipcc_coverage(run_id)
            update_primary_topic(run_id)

        stat.status = 3
        stat.save()
