# Allocate paragraphs to users

import os, sys, time, resource, re, gc, shutil, datetime
import django
import numpy as np
sys.path.append('/home/galm/software/django/tmv/BasicBrowser/')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()
from scoping.models import *

projectid = 27
queryid = 2823
tagid = 650
# Users
# galm:  1
# minj:  3
# hilj:  7
# nemet: 9
userids = [
    ('hilj', 600),
    ('minj', 200),
    ('delm', 200),
    ('galm', 200),
    ('nemet', 200),
    ('ludg', 200),
    ('rogj', 200),
    ('edmj', 10)
]

usernames=[]
nbparalloc=[]
for a,b in userids:
    usernames.append(a)
    nbparalloc.append(b)

nbparalloc =    np.cumsum(nbparalloc)

# Get all unprocessed paragraphs
p      = Project.objects.get(pk=projectid)
q      = Query.objects.get(pk=queryid)
users  = User.objects.filter(query=q).order_by('id')
nusers = users.count()
t      = Tag.objects.get(pk=tagid)
dos    = DocOwnership.objects.filter(tag=t,relevant=0)
dos.count()

# Get all associated documents
docpars = DocPar.objects.filter(docownership__id__in=dos)
docs    = Doc.objects.filter(docpar__id__in=docpars).distinct()

# Reallocate documents + paragraphs to users so that each user get roughly the same number of items
print("{} documents".format(docs.count()))
print("{} paragraphs".format(docpars.distinct().count()))
print(users.values())

counter = 1
for i, doc in enumerate(docs):
     dps  = docpars.filter(doc=doc).order_by('n')
     #user = users[i%nusers]
     try:
         uname = usernames[(nbparalloc > counter).tolist().index(True)]
     except:
         uname = "hilj"
     curuser = User.objects.filter(
        query   = q,
        username= uname).get()
     print(doc.title)
     print("reassigning {} docpars ".format(dps.count()))
     for dp in dps:
         do = dos.get(docpar=dp)
         do.user=curuser
         do.date=datetime.datetime.now()
         do.save()

         counter = counter +1
