from __future__ import print_function

from django.core.management.base import BaseCommand, CommandError
from django.core import management
from parliament.models import *

import os
import re
import logging
import requests
import dataset
from lxml import html
from urllib.parse import urljoin
from normdatei.text import clean_text, clean_name, fingerprint
from normdatei.parties import search_party_names

from plpr_scraper import *




class Command(BaseCommand):
    help = 'import the protocols'

    #def add_arguments(self, parser):
        #parser.add_argument('-l','--list', nargs='+', help='<Required> list', required=True)


    def handle(self, *args, **options):
        print("protocols!")
