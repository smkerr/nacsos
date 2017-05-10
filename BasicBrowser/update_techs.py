import django, os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

technologies = Technology.objects.all()

for t in technologies:
    t.queries = t.query_set.count()
    tdocs = Doc.objects.filter(technology=t)
    itdocs = Doc.objects.filter(query__technology=t,query__type="default")
    tdocs = tdocs | itdocs
    t.docs = tdocs.distinct().count()
    t.nqs = t.queries
    t.ndocs = t.docs
    t.save()
