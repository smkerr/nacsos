from django.shortcuts import render
import os, time

# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import loader
from django.utils import timezone
from django.urls import reverse

from .models import *

def index(request):
    template = loader.get_template('scoping/index.html')
    queries = Query.objects.all()
    context = {
        'queries': queries,
    }
    return HttpResponse(template.render(context, request))

import subprocess
import sys
def doquery(request):
    template = loader.get_template('scoping/index.html')
    qtitle = request.POST['qtitle']
    qtext = request.POST['qtext']
    q = Query(
        title=qtitle,
        text=qtext,
        date=timezone.now()
    )
    q.save()
    qid = q.id 
    fname = "queries/"+qtitle+".txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)

    command = "scrapeQuery "+fname

    subprocess.Popen(["scrapeQuery.py", fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id}))

def querying(request, qid):

    template = loader.get_template('scoping/query_progress.html')

    query = Query.objects.get(pk=qid)
    logfile = "queries/"+query.title+".log"

    wait = True
    # wait up to 15 seconds for the log file, then go to a page which displays its contents
    for i in range(15):
        try:
            with open(logfile,"r") as lfile:
                log = lfile.readlines()
            break
        except:
            log = ["oops, there seems to be some kind of problem, I can't find the log file"]
            time.sleep(1)

    finished = False
    if "done!" in log[-1]:
        finished = True

    docs = Doc.objects.filter(query__id=qid)
    doclength = len(docs)

    context = {
        'log': log,
        'finished': finished,
        'docs': docs,
        'doclength': doclength,
        'query': query
    }
    return HttpResponse(template.render(context, request))

def query(request,qid):
    template = loader.get_template('scoping/query.html')
    query = Query.objects.get(pk=qid)

    tags = Tag.objects.filter(query=query)

    tags = tags.values()

    for tag in tags:
        #docs = Doc.objects.filter(tag=tag).count()
        tag['docs'] = Doc.objects.filter(tag=tag['id']).count()
  
    fields = ['id','title','text']

    untagged = Doc.objects.filter(tag__isnull=True).count()

    users = User.objects.all()

    proj_users = users.query

    user_list = []
    
    for u in users:
        if query in u.query_set.all():
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': True
            })
        else:
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': False
            })

    context = {
        'query': query,
        'tags': list(tags),
        'fields': fields,
        'untagged': untagged,
        'users': user_list
    }
    return HttpResponse(template.render(context, request))

##################################################
## View all docs

def doclist(request,qid):

    template = loader.get_template('scoping/docs.html')

    query = Query.objects.get(pk=qid)
    qdocs = Doc.objects.filter(query__id=qid)
    all_docs = qdocs
    ndocs = all_docs.count()

    docs = list(all_docs[:100].values('wosarticle__ti','wosarticle__ab','wosarticle__py'))    

    fields = []

    for f in Doc._meta.get_fields():
        if f.is_relation:
            for rf in f.related_model._meta.get_fields():
                if not rf.is_relation:
                    path = f.name+"__"+rf.name
                    fields.append({"path": path, "name": rf.verbose_name})

    basic_fields = ['Title', 'Abstract', 'Year']

    context = {
        'query': query,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'ndocs': ndocs
    }
    return HttpResponse(template.render(context, request))

##################################################
## Ajax function, to return sorted docs

from django.db.models.aggregates import Aggregate
class StringAgg(Aggregate):
    function = 'STRING_AGG'
    template = "%(function)s(%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, delimiter, **extra):
        super(StringAgg, self).__init__(expression, delimiter=delimiter, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value

def sortdocs(request):

    qid = request.GET.get('qid',None)
    fields = request.GET.getlist('fields[]',None)
    field = request.GET.get('field',None)
    sortdir = request.GET.get('sortdir',None)
    extra_field = request.GET.get('extra_field',None)

    f_fields = request.GET.getlist('f_fields[]',None)
    f_operators = request.GET.getlist('f_operators[]',None)
    f_text = request.GET.getlist('f_text[]',None)
    f_join = request.GET.getlist('f_join[]',None)

    tag_title = request.GET.get('tag_title',None)

    # get the query
    query = Query.objects.get(pk=qid)

    # filter the docs according to the query
    all_docs = Doc.objects.filter(query__id=qid)
    filt_docs = Doc.objects.filter(query__id=qid)

    tag_text = ""
    # filter the docs according to the currently active filter
    for i in range(len(f_fields)):
        if i==0:
            joiner = "AND"
            text_joiner = ""
        else:
            joiner = f_join[i-1]
            text_joiner = f_join[i-1]
        if f_operators[i] == "noticontains":
            op = "icontains"
            exclude = True
        else:
            op =  f_operators[i] 
            exclude = False  
        try:
            kwargs = {
                '{0}__{1}'.format(f_fields[i],op): f_text[i]
            } 
            if joiner=="AND":
                if exclude:
                    filt_docs = filt_docs.exclude(**kwargs)
                else:
                    filt_docs = filt_docs.filter(**kwargs)
            else:
                if exclude:
                    filt_docs = filt_docs | all_docs.exclude(**kwargs)
                else:
                    filt_docs = filt_docs | all_docs.exclude(**kwargs)
            tag_text+= '{0} {1} {2} {3}'.format(text_joiner, f_fields[i], f_operators[i], f_text[i])
        except:
            break

    if tag_title is not None:
        t = Tag(title=tag_title)
        t.text = tag_text
        t.query = query
        t.save()
        for doc in filt_docs:
            doc.tag.add(t)
        return(JsonResponse("",safe=False))

    if sortdir=="+":
        sortdir=""

    fields = tuple(fields)

    single_fields = []
    mult_fields = []
    for f in fields:
        if "docauthinst" in f:
            mult_fields.append(f)
        else:
            single_fields.append(f)
    single_fields = tuple(single_fields)
    #mult_fields = tuple(mult_fields)

    #print(mult_fields)
        
    mult_fields=[]

    if sortdir is not None:
        null_filter = field+'__isnull'
        docs = filt_docs.filter(**{null_filter:False}).order_by(sortdir+field)[:100].values(*fields)
    else:
        docs = filt_docs[:100].values(*fields)
        if len(mult_fields) > 0:
            
            docs = filt_docs(query__id=qid)[:100].values(*single_fields).annotate(
                da=StringAgg(mult_fields[0],"; "),
            )
            for d in docs:
                d[mult_fields[0]]=d['da']

    response = {
        'data': list(docs),
        'n_docs': filt_docs.count()    
    }

    return JsonResponse(response,safe=False)

def activate_user(request):

    qid = request.GET.get('qid',None)
    checked = request.GET.get('checked',None)
    user = request.GET.get('user',None)

    query = Query.objects.get(pk=qid)
    user = User.objects.get(username=user)

    if checked=="true":       
        query.users.add(user)
        query.save()
        response=1
    else:
        response=-1
        query.users.remove(user)

    return JsonResponse(response,safe=False)




