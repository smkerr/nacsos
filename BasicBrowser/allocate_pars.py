# Allocate paragraphs to users

import os, sys, time, resource, re, gc, shutil, datetime
import django
sys.path.append('/home/galm/software/django/tmv/BasicBrowser/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()
from scoping.models import *

projectid = 27
queryid = 2777
tagid = 646
# Users
# galm:  1
# minj:  3
# hilj:  7
# nemet: 9
userids = [
    ('hilj', 0.75),    # hilj gets 800 paragraphs
    ('minj', 0.25)     # minj gets 400 paragraphs
]

# Get all unprocessed paragraphs
p = Project.objects.get(pk=projectid)
q = Query.objects.get(pk=queryid)
users = User.objects.filter(query=q).order_by('id')
nusers = users.count()
t = Tag.objects.get(pk=tagid)
dos = DocOwnership.objects.filter(tag=t,relevant=0)
dos.count()

# Get all associated documents
docpars = DocPar.objects.filter(docownership__id__in=dos)
docs = Doc.objects.filter(docpar__id__in=docpars).distinct()

# Reallocate documents + paragraphs to users so that each user get roughly the same number of items
print("{} documents".format(docs.count()))
print("{} paragraphs".format(docpars.distinct().count()))
print(users.values())


for i, doc in enumerate(docs):
     dps = docpars.filter(doc=doc).order_by('n')
     user = users[i%nusers]
     print(doc.title)
     print("reassigning {} docpars ".format(dps.count()))
     for dp in dps:
         do = dos.get(docpar=dp)
         do.user=user
         do.date=datetime.datetime.now()
         do.save()
