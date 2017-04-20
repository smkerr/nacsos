import django, os, sys, time, resource, re, gc, shutil
from django.utils import timezone
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

lubs = User.objects.get(username="lubs")

lubdocs = DocOwnership.objects.filter(user=lubs)

ylubdocs = lubdocs.filter()

query = lubdocs.first().query


t = Tag(title="recheck_sss",query=query)
t.save()

i = 0
for d in ylubdocs:
    i+=1
    if d.doc.note_set.all().count() > 0:
        for n in d.doc.note_set.all():
            if "SSS" in n.text:
                break
    if d.relevant==1:
        d.doc.tag.add(t)
