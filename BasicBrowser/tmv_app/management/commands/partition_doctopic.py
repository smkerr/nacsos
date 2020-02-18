from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from tmv_app.models import *

class Command(BaseCommand):
    help = 'copy doctopics'

    def handle(self, *args, **options):
        run_ids = list(RunStats.objects.all().order_by('run_id').values_list('run_id',flat=True))
        run_ids = list(RunStats.objects.filter(run_id__gt=2714).order_by('run_id').values_list('run_id',flat=True))
        p_runs = []
        p_rows = 0
        f_run = 0
        row_max = 10000000
        #n_rows = 372764866
        for run_id in run_ids:
            if f_run ==0:
                f_run = run_id
            rrows = DocTopic.objects.filter(run_id=run_id).count()
            p_rows+=rrows
            p_runs.append(run_id)
            if (p_rows > row_max and len(p_runs) > 1) or run_id == run_ids[-1]:

                l_run = run_id

                pname = f"pt{f_run}_{l_run}"

                print("copying partion", pname, flush=True)

                try:
                    connection.schema_editor().add_range_partition(
                        model = DocTopicPartitioned,
                        name = pname,
                        from_values = f_run,
                        to_values = l_run
                    )
                except:
                    print("could not create partition", pname, flush=True)
                    f_run = l_run
                    p_rows = 0
                    p_runs = []
                    continue

                # if f_run>628:
                #     connection.schema_editor().delete_partition(
                #         model=DocTopicPartitioned,
                #         name=pname,
                #     )

                q = f"(SELECT * FROM tmv_app_doctopic WHERE run_id >= {f_run} AND run_id < {l_run})"
                with connection.cursor() as cursor:
                    cursor.execute(f"COPY {q} TO '/var/lib/postgresql/doctopic.gz' WITH (FORMAT 'binary');")
                    #cursor.execute(f"INSERT INTO tmv_app_doctopicpartitioned_{pname} {q};")


                iq = f"COPY tmv_app_doctopicpartitioned_{pname} FROM '/var/lib/postgresql/doctopic.gz' WITH (FORMAT 'binary');"
                with connection.cursor() as cursor:
                    cursor.execute(iq)

                f_run = l_run
                p_rows = 0
                p_runs = []
