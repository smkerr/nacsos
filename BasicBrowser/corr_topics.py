import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

from django.utils import timezone
import subprocess
import pandas as pd
import numpy as np

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *
from tmv_app.models import *

def main():
    run_id = sys.argv[1]
    print(run_id)

    dts = DocTopic.objects.filter(run_id=run_id)

    df = pd.DataFrame(list(dts.values('doc_id','topic_id','scaled_score')))

    df = df.pivot(index='doc_id',columns='topic_id',values='scaled_score')
    #df = df.pivot(index='topic_id',columns='doc_id',values='scaled_score')

    # pseudo code for docwise:
    # There are 96 billion combinations, so need to limit
    # For each doc, compare with docs that have a topic_score > 0 of the
    # Largest topic in the doc.

    corr = df.corr()
    values = corr.values
    cols = corr.columns

    for c in range(len(cols)):
        topic = cols[c]
        tcor = values[c]
        for tc in range(len(tcor)):
            corrtopic = cols[tc]
            corrscore = tcor[tc]
            if corrscore > 0:
                topiccorr, created = TopicCorr.objects.get_or_create(
                    topic_id=topic, topiccorr=corrtopic, run_id=run_id
                )
                topiccorr.score = corrscore
                topiccorr.save()


if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
