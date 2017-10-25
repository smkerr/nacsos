from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from tmv_app.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer
from time import time

from utils.utils import *# flatten
from django.db import connection, transaction
cursor = connection.cursor()
from psycopg2.extras import *
from psycopg2.extras import execute_values

class Command(BaseCommand):
    help = 'do open heart surgery on database'

    def handle(self, *args, **options):

        def insert_many(values_list,dc_id):
            query='''
                INSERT INTO "tmv_app_doctopic_copy"
                ("doc_id", "topic_id", "score", "scaled_score", "run_id")
                VALUES (dc_id,%s,%s,%s,%s)
            '''
            cursor = connection.cursor()
            cursor.executemany(query,values_list)

        remove_index = [
            'DROP INDEX tmv_app_doctopic_copy_doc_id_690187c5;',
            'DROP INDEX tmv_app_doctopic_copy_run_id_ca885d80;',
            'DROP INDEX tmv_app_doctopic_copy_topic_id_129443cf;'
        ]
        create_index = [
            '''
            CREATE INDEX tmv_app_doctopic_copy_doc_id_690187c5
                ON tmv_app_doctopic_copy
                USING btree
                (doc_id);
            ''',
            '''
            CREATE INDEX tmv_app_doctopic_copy_run_id_ca885d80
                ON tmv_app_doctopic_copy
                USING btree
                (run_id);
            ''',
            '''
            CREATE INDEX tmv_app_doctopic_copy_topic_id_129443cf
                ON tmv_app_doctopic_copy
                USING btree
                (topic_id);
            '''
        ]
        for ind in remove_index:
            cursor = connection.cursor()
            try:
                cursor.execute(ind)
            except:
                print("no index")

        dids =  list(set(list(Doc.objects.filter(
            doctopic__isnull=False
        ).values_list('UT',flat=True))))

        docs = Doc.objects.filter(UT__in=dids)


        for doc in docs.iterator():
            dc = dc = Doc_2.objects.get(
                UT__UT=doc.UT
            )
            dts = DocTopic.objects.filter(doc=doc).annotate(
                dc_id = models.Value(dc.id, models.IntegerField())
            )

            dts = list(dts.values_list('dc_id','topic_id','score','scaled_score','run_id'))
            execute_values(
                cursor,
                "INSERT INTO tmv_app_doctopic_copy (doc_id, topic_id, score, scaled_score, run_id) VALUES %s",
                dts
            )

        for ind in create_index:
            cursor = connection.cursor()
            try:
                cursor.execute(ind)
            except:
                print("no index")

            #insert_many(dts, dc.id)

            # pool = Pool(processes=ps)
            # pool.map(insert_many,values_list)
            # pool.terminate()
