from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer

from utils.utils import *# flatten

class Command(BaseCommand):
    help = 'remove duplicates interactively'


    def handle(self, *args, **options):

        sdocs = Doc.objects.exclude(UT__contains="WOS:",wosarticle__di__isnull=True)[:50]
        for s in sdocs.iterator():
            docs = []
            py_docs = Doc.objects.exclude(UT=s.UT).filter(PY=s.PY)

            s1 = shingle(s.title)

            for d in py_docs:
                j = jaccard(s1,d.shingle())
                if j > 0.51:
                    docs.append(d)

            if len(docs)>0:
                print("{}: {} , from queries {} \n \
                \nmatches the following: ".format(
                    s.UT,
                    s.title,
                    "; ".join([x.title for x in s.query.all()])
                ))
                i = 0
                for d in docs:
                    print(
                        "{}: {} {}, from queries {}".format(
                            i,
                            d.UT,
                            d.title,
                            "; ".join([x.title for x in d.query.all()])
                        )
                    )
                    print('##########\n')
                    print("I'm going to give you a choice of which to delete now,\n\
press \"o\" for the original, or a number for the numbered duplicate\n\
to delete. Or enter \"s\" to skip")
                    print("You can combine choices in a list like [o,0,1,2]")
                    x = input('What do you want to delete?: ')

                    try:
                        x = list(x)
                        for el in x:
                            if el=="o":
                                ut = s.UT
                                s.delete()
                                print("deleted {}".format(ut))
                                continue
                            elif isinstance(el, int):
                                ut = docs[el].UT
                                docs[el].delete()
                                print("deleted {}".format(ut))
                            else:
                                y = abcsd
                    except:
                        print("sorry I didn't manage to understand what you meant\n\
or didn't manage to act on it, I'm just goin to move on now...")
