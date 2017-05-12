import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

from django.utils import timezone
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *
from scoping.views import *

def main():

    # Get technology ID from kwargs
    tid  = sys.argv[1] # Query containing list of documents
    # Get all the technology relevant docs (scopus)
    tech, docs, tobj = get_tech_docs(tid)
    docs = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech,
        scopus=True
    )

    # Scrape them (and wait)

    # go through upload_docrefs_scopus, without adding, only saving text of ones
    # that are not in db.

    # filter for query matchers

    # Check for nodb refs

    # save them somewhere

    # Page says waiting, or lists these refs
