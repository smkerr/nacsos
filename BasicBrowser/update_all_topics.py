#!/usr/bin/env python3

# onlinewikipedia.py: Demonstrates the use of online VB for LDA to
# analyze a bunch of random Wikipedia articles.
#
# Copyright (C) 2010  Matthew D. Hoffman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pickle, string, numpy, getopt, sys, random, time, re, pprint, gc, os
import pandas as pd
import subprocess
import onlineldavb
import scrapeWoS
import gensim
import nltk
import sys
import time
from multiprocess import Pool
import django
sys.stdout.flush()


# import file for easy access to browser database
sys.path.append('/home/galm/software/tmv/BasicBrowser/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from tmv_app.views import *
from tmv_app.models import *

session = {}

# Select last run
for stat in RunStats.objects.filter(run_id__gt=50):
    run_id = stat.run_id
    print(run_id)
    # Set current sums for run to False (so recalculated)
    stat.topic_titles_current = False
    stat.topic_year_scores_current = False
    stat.topic_scores_current = False
    stat.save()

    update_year_topic_scores(run_id)
    update_topic_scores(run_id)
    update_topic_titles(run_id)
    subprocess.Popen(["python3",
        "/home/galm/software/tmv/BasicBrowser/corr_topics.py",
        str(run_id)
    ]).wait()
