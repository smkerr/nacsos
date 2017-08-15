from django.core.management.base import BaseCommand, CommandError
from tmv_app.models import *
import numpy as np
from sklearn.decomposition import NMF
from scipy.sparse import csr_matrix, find
from functools import partial
from multiprocess import Pool
from utils.db import *
from utils.utils import *
from scoping.models import *
from time import time
import gc, sys
from django.core import management
import pandas as pd


class Command(BaseCommand):
    help = 'rerun a dynamic topic model with a different number \
    or dynamic topics'

    def add_arguments(self, parser):
        parser.add_argument('a',type=int)
        parser.add_argument('z',type=int)


    def handle(self, *args, **options):
        a = options['a']
        z = options['z'] + 1

        runs = list(range(a,z))

        stat = RunStats.objects.get(pk=a)

        if stat.method == "DT":
            dynamic = True
        else:
            dynamic = False


        col1s = []
        col2s = []
        ss = []
        scols = []

        for i in range(1,len(runs)):

            if dynamic==True:
                topics1 = DynamicTopic.objects.filter(run_id=runs[i-1])
                topics2 = DynamicTopic.objects.filter(run_id=runs[i])
            else:
                topics1 = Topic.objects.filter(run_id=runs[i-1])
                topics2 = Topic.objects.filter(run_id=runs[i])


            df = pd.DataFrame.from_dict(list(topics2.values('title','score')))
            df2 = pd.DataFrame.from_dict([{'title': 'None','score': 0}])
            df = df.append(df2)
            col1 = "run_{}_topics_{}".format(runs[i-1],topics1.count())
            scol = "scores_{}".format(runs[i])
            bscol = "scores_{}".format(runs[i-1])

            if i==1:
                scols.append(bscol)

            col1s.append(col1)
            scols.append(scol)

            col2 = "run_{}_topics_{}".format(runs[i], topics2.count())

            col2s.append(col2)

            s = "similarity_{}-{}".format(runs[i-1],runs[i])
            ss.append(s)

            df = df.rename(columns = {'title': col2, 'score': scol})

            df[s] = 0
            df[col1] = "None"
            df[bscol] = 0

            for t in topics2:
                scores = [0]
                titles = [""]
                tscores = [0]
                for ct in topics1:
                    score = len(set(t.top_words).intersection(set(ct.top_words)))
                    if score>0:
                        scores.append(score)
                        titles.append(ct.title)
                        tscores.append(ct.score)


                m = max(scores)
                df.loc[df[col2]==t.title, s] = m
                if m==0:
                    df.loc[df[col2]==t.title, col1] = 'None'
                else:
                    df.loc[df[col2]==t.title, col1] = titles[scores.index(max(scores))]
                    df.loc[df[col2]==t.title, bscol] = tscores[scores.index(max(scores))]


            if i==1:
                #df = pd.DataFrame.from_dict(list(topics2.values('title')))
                mdf = df
            else:
                mdf = mdf.merge(df,how="outer").fillna("")


        columns = []
        for i in range(len(col1s)):
            columns.append(col1s[i])
            columns.append(scols[i])
            columns.append(ss[i])
            if i == len(col1s)-1:
                columns.append(col2s[i])
                columns.append(scols[i+1])

        print(columns)

        mdf = mdf[columns]


        res = mdf.groupby(columns)
        res = res.apply(lambda x: x.sort_values(s,ascending=False))

        l = len(res)

        fname = "/tmp/run_compare_{}_{}.xlsx".format(runs[0],runs[len(runs)-1])

        writer = pd.ExcelWriter(fname, engine='xlsxwriter')

        res.to_excel(writer)

        worksheet = writer.sheets['Sheet1']

        for i in range(len(ss)):
            if (i+1)*3 > 26:
                c = 'A'+chr(ord('A')-1+((i+1)*3)-26)
            else:
                c = chr(ord('A')-1+(i+1)*3)
            r = "{}2:{}{}".format(c,c,len(res))
            print(r)

            worksheet.conditional_format(r, {
                'type': '3_color_scale',
                'min_value': 0,
                'mid_value': 5,
                'max_value': 10,
                'min_type': 'num',
                'mid_type': 'num',
                'max_type': 'num',
            })

        writer.save()

        return(fname)
