from django.shortcuts import render
import os, time, math

# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import loader
from django.utils import timezone
from django.urls import reverse

from .models import *

@login_required
def index(request):
    template = loader.get_template('scoping/index.html')
    queries = Query.objects.all()
    context = {
        'queries': queries,
    }
    return HttpResponse(template.render(context, request))

import subprocess
import sys
@login_required
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

@login_required
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

@login_required
def query(request,qid):
    template = loader.get_template('scoping/query.html')
    query = Query.objects.get(pk=qid)

    tags = Tag.objects.filter(query=query)

    tags = tags.values()

    for tag in tags:
        #docs = Doc.objects.filter(tag=tag).count()
        tag['docs'] = Doc.objects.filter(tag=tag['id']).count()
        tag['a_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],).count()       
        if tag['a_docs'] == 0:
            tag['a_docs'] = False
        else:
            tag['seen_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant__gt=0).count() 
            tag['rel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=1).count()    
            tag['relevance'] = round(tag['rel_docs']/tag['seen_docs']*100)
  
    fields = ['id','title','text']

    untagged = Doc.objects.filter(tag__isnull=True).count()

    users = User.objects.all()

    proj_users = users.query

    user_list = []

    user_docs = {}
    
    for u in users:
        tdocs = DocOwnership.objects.filter(query=query,user=u)
        user_docs['tdocs'] = tdocs.count()
        user_docs['reldocs'] = tdocs.filter(relevant=1).count()
        user_docs['irreldocs'] = tdocs.filter(relevant=2).count()
        user_docs['maybedocs'] = tdocs.filter(relevant=3).count()
        user_docs['checked_percent'] = round((user_docs['reldocs'] + user_docs['irreldocs'] + user_docs['maybedocs']) / user_docs['tdocs'] * 100)
        if query in u.query_set.all():
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': True,
                'user_docs': user_docs
            })
        else:
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': False,
                'user_docs': user_docs
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
@login_required
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

@login_required
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

@login_required
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

def assign_docs(request):
    qid = request.GET.get('qid',None)
    users = request.GET.getlist('users[]',None)
    tags = request.GET.getlist('tags[]',None)
    proportion = float(request.GET.get('proportion',None))

    query = Query.objects.get(pk=qid)  

    user_list = []

    for user in users:
        user_list.append(User.objects.get(username=user))


    for tag in tags:
        t = Tag.objects.get(pk=tag)
        docs = Doc.objects.filter(query=query,tag=t)
        ndocs = docs.count()
        ssize = math.ceil(ndocs*proportion)
        sample = docs.order_by('?')[:ssize]
        for s in range(len(sample)):
            doc = sample[s]
            user = user_list[s % len(user_list)]
            docown = DocOwnership(doc=doc,query=query,user=user)
            docown.save()

    return HttpResponse("bla")

def check_docs(request,qid):

    query = Query.objects.get(pk=qid)  
    user = request.user
    docs = Doc.objects.filter(query=query,users=user.id,docownership__relevant=0)

    ndocs = docs.count()
    doc = docs.first()

    authors = DocAuthInst.objects.filter(doc=doc)

    template = loader.get_template('scoping/doc.html')
    context = {
        'query': query,
        'doc': doc,
        'ndocs': ndocs,
        'user': user,
        'authors': authors
    }
    return HttpResponse(template.render(context, request))

def review_docs(request,qid):

    query = Query.objects.get(pk=qid)  
    user = request.user
    docs = Doc.objects.filter(query=query,users=user.id,docownership__relevant__gt=0)

    ndocs = docs.count()
    doc = docs.first()

    authors = DocAuthInst.objects.filter(doc=doc)

    template = loader.get_template('scoping/doc.html')
    context = {
        'query': query,
        'doc': doc,
        'ndocs': ndocs,
        'user': user,
        'authors': authors
    }
    return HttpResponse(template.render(context, request))

from django.core.mail import send_mail

def do_review(request):

    qid = request.GET.get('query',None)
    doc_id = request.GET.get('doc',None)
    d = request.GET.get('d',None)

    doc = Doc.objects.get(pk=doc_id)
    query = Query.objects.get(pk=qid)  
    user = request.user

    docown = DocOwnership.objects.filter(doc=doc,query=query,user=user).first()
    docown.relevant=d
    docown.save()


   
    return HttpResponse("")
	




