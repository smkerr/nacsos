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


a = int(sys.argv[1])

z = int(sys.argv[2])

for s in RunStats.objects.filter(run_id__gte=a,run_id__lte=z).iterator():
    print(s)
    print(s.pk)
    Topic.objects.filter(run_id=s).delete()
    DocTopic.objects.filter(run_id=s.pk).delete()
    TopicTerm.objects.filter(run_id=s.pk).delete()
    s.delete()
