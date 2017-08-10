from tmv_app.models import *
from scoping.models import *
from django.utils import timezone

def f_dlambda(t,m,v_ids,t_ids,run_id):
    tt = DynamicTopicTerm(
        term_id = v_ids[m[1][t]],
        topic_id = t_ids[m[0][t]],
        score = m[2][t],
        run_id = run_id
    )
    return tt


def init(n_f):
    try:
        stats = RunStats.objects.all().last()
        settings = Settings.objects.all().first()
        run_id = stats.run_id
    except:
        settings = Settings(
            doc_topic_score_threshold=1,
            doc_topic_scaled_score=True
        )
        run_id = 0

    run_id +=1

    stats = RunStats(
        run_id = run_id,
        start=timezone.now(),
        batch_count=0,
        last_update=timezone.now(),
        ngram=1,
        max_features=n_f
    )
    stats.save()

    settings.run_id = run_id
    settings.save()

    return(run_id)
