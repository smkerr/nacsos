from django.shortcuts import render, render_to_response
import os, time, math, itertools, csv, random
from itertools import chain
from django.db.models import Max
from django.db.models import Func, F
from django.db.models.functions import Concat
# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import loader, RequestContext
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
import json
from django.apps import apps

from .models import *

def super_check(user):
    return user.groups.filter(name__in=['superuser'])


@login_required
def switch_mode(request):

    if request.session['appmode']=='scoping':
        request.session['appmode']='snowballing'
        return HttpResponseRedirect(reverse('scoping:snowball'))
    else:
        request.session['appmode']='scoping'
        return HttpResponseRedirect(reverse('scoping:index'))



########################################################
## Homepage - list the queries, form for adding new ones

@login_required
def index(request):
    request.session['DEBUG'] = False
    request.session['appmode']='scoping'

    template = loader.get_template('scoping/index.html')

    queries_none  = Query.objects.all().filter(type=None)
    queries_dft   = Query.objects.all().filter(type="default")
    queries       = queries_none | queries_dft
    queries       = queries.order_by('-id')
    query         = queries.last()
    users         = User.objects.all()
    technologies  = Technology.objects.all()

    for q in queries:
        q.tech = q.technology
        if q.technology==None:
            q.tech="None"
        else:
            q.tech=q.technology.name
        #print(q.tech)

    if request.user.username in ["galm","roger","nemet"]:
        extended=True
    else:
        extended=False

    context = {
      'queries'      : queries,
      'query'        : query,
      'users'        : users,
      'active_users' : users.filter(username=request.user.username),
      'techs'        : technologies,
      'appmode'      : request.session['appmode'],
      'extended'     : extended,
      'innovations'  : Innovation.objects.all()
    }

    return HttpResponse(template.render(context, request))

########################################################
## Tech Homepage - list the technologies, form for adding new ones

@login_required
def technologies(request):

    template = loader.get_template('scoping/tech.html')

    technologies = Technology.objects.all()

    users = User.objects.all()
    refresh = False
    subprocess.Popen(["python3", "/home/galm/software/tmv/BasicBrowser/update_techs.py"], stdout=subprocess.PIPE)
    for t in technologies:
        t.queries = t.query_set.count()
        tdocs = Doc.objects.filter(technology=t)
        if refresh==True:
            tdocs = Doc.objects.filter(technology=t)
            itdocs = Doc.objects.filter(query__technology=t,query__type="default")
            tdocs = tdocs | itdocs
            t.docs = tdocs.distinct().count()
            t.nqs = t.queries
            t.ndocs = t.docs
            t.save()
        else:
            t.docs = t.ndocs

    context = {
      'techs'    : technologies,
      'users'    : users
    }

    return HttpResponse(template.render(context, request))

########################################################
## edit tech query

@login_required
def technology_query(request):

    tid = request.GET.get('tid', None)
    qid = request.GET.get('qid', None)

    q = Query.objects.get(pk=qid)
    if tid=="None":
        q.technology = None
    else:
        t = Technology.objects.get(pk=tid)
        q.technology = t

    q.save()

    return HttpResponse("")

@login_required
def innovation_query(request):

    iid = request.GET.get('tid', None)
    qid = request.GET.get('qid', None)

    q = Query.objects.get(pk=qid)
    if iid=="None":
        q.innovation = None
    else:
        i = Innovation.objects.get(pk=iid)
        q.innovation = i

    q.save()

    return HttpResponse("")

########################################################
## Snowballing homepage
@login_required
def snowball(request):
    request.session['DEBUG'] = True
    request.session['appmode']='snowballing'

    template        = loader.get_template('scoping/snowball.html')

    # Get SBS information
    sb_sessions     = SnowballingSession.objects.all().order_by('-id')

    # Get latest step associated with each SB sessions
    sb_session_last = sb_sessions.last()

    for sbs in sb_sessions:
        try:
            sb_qs = sbs.query_set.all().order_by('id')
            seedquery = sb_qs.first()
            step  = "1"
            nbdocsel = 0
            nbdoctot = 0
            nbdocrev = 0
            sbs.ns = sb_qs.aggregate(Max('step'))['step__max']
            sbs.lq = sb_qs.last().id
            sbs.rc = sb_qs.last().r_count
            sbs.ndsel = Doc.objects.filter(docownership__query__snowball=sbs,docownership__relevant=1).distinct().count()
            sbs.ndtot = DocRel.objects.filter(seedquery=seedquery).count()
            sbs.ndrev = Doc.objects.filter(docownership__query__snowball=sbs,docownership__relevant=0).distinct().count()
        except:
            pass

    # Get technologies
    technologies = Technology.objects.all()

    context = {
        'sb_sessions'    : sb_sessions,
        'sb_session_last': sb_session_last,
        'techs'          : technologies
    }
    return HttpResponse(template.render(context, request))

#########################################################
## Test the SSH connection
def ssh_test():

    NoSSHTest = False

    if NoSSHTest :
      ssh_working = True
    else :
      ssh_working = subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/check_selenium_ip.py", "-b", "chrome"], stdout=subprocess.PIPE).communicate()[0].strip().decode()
      print(repr(ssh_working))
    if ssh_working == "False":
        subprocess.Popen(["setsid","ssh","-D","1080","minx@aix.pik-potsdam.de"])
    return(ssh_working)

########################################################
## Add the technology
@login_required
def add_tech(request):
    tname = request.POST['tname']
    tdesc  = request.POST['tdesc']
    #  create a new query record in the database
    t = Technology(
        name=tname,
        description=tdesc
    )
    t.save()
    return HttpResponseRedirect(reverse('scoping:technologies'))

########################################################
## update the technology
@login_required
def update_tech(request):

    tid = request.POST['tid']
    tname = request.POST['tname']
    tdesc  = request.POST['tdesc']
    #  create a new query record in the database
    t = Technology.objects.get(pk=tid)
    t.name=tname
    t.description=tdesc
    t.save()
    return HttpResponseRedirect(reverse('scoping:technologies'))



#########################################################
## Do the query
import subprocess
import sys
@login_required
def doquery(request):

    #ssh_test()

    qtitle = request.POST['qtitle']
    qdb    = request.POST['qdb']
    qtype  = request.POST['qtype']
    qtext  = request.POST['qtext']

    #  create a new query record in the database
    q = Query(
        title=qtitle,
        type=qtype,
        text=qtext,
        creator = request.user,
        date = timezone.now(),
        database = qdb
    )
    q.save()

    if qdb=="intern":
        args = qtext.split(" ")
        q1 = Doc.objects.filter(query=args[0])
        op = args[1]
        q2 = Doc.objects.filter(query=args[2])
        if op =="AND":
            combine = q1.filter(query=args[2])
        if op =="OR":
            combine = q1 | q2
        if op == "NOT":
            combine = q1.exclude(query=args[2])
        for d in combine.distinct('UT'):
            d.query.add(q)

        q.r_count = len(combine.distinct('UT'))
        q.save()

        return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': q.id, 'q2id': 0, 'sbsid': 0}))


    else:
        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,encoding='utf-8',mode="w") as qfile:
            qfile.write(qtext.encode("utf-8").decode("utf-8"))

        time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 0, 'docadded': 0, 'q2id': 0}))

#########################################################
## Start snowballing
import subprocess
import sys
@login_required
def start_snowballing(request):

    # Get form content
    qtitle = request.POST['sbs_name']
    qtext  = request.POST['sbs_initialpearls']
    qdb    = request.POST['qdb']
    qtech  = request.POST['sbs_technology']

    curdate = timezone.now()

    # Get technology
    t = Technology.objects.get(pk=qtech)

    # Create new snowballing session
    sbs = SnowballingSession(
      name = qtitle,
      database = qdb,
      initial_pearls = qtext,
      date=curdate,
      status=0,
      technology=t
    )
    sbs.save()
    if request.session['DEBUG']:
        print("start_snowballing: New SBS successfully created.")


    #  create 2 new query records in the database (one for the bakward search and one for the forward search)
    q = Query(
        title=qtitle+"_backward_1_1",
        database=qdb,
        type='backward',
        text=qtext,
        date=curdate,
        snowball=sbs,
        step=1,
        substep=1,
        technology=t
    )
    q.save()
    if request.session['DEBUG']:
        print("start_snowballing: New backward query #"+str(q.id)+" successfully created.")

    # write the query into a text file
    fname = "/queries/"+str(q.id)+".txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)

    # run "scrapeQuery.py" on the text file in the background
    if request.session['DEBUG']:
        print("start_snowballing: starting scraping process on "+q.database+" (backward query).")
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    #####
    ## This bit starts up the forward snowballing

    q2 = Query(
        title=qtitle+"_forward_1_2",
        database=qdb,
        type='forward',
        text=qtext,
        date=curdate,
        snowball=sbs,
        step=1,
        substep=2,
        technology=t
    )
    q2.save()
    if request.session['DEBUG']:
        print("start_snowballing: New forward query #"+str(q2.id)+" successfully created.")

    # write the query into a text file
    fname = "/queries/"+str(q2.id)+".txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)

    time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    if request.session['DEBUG']:
        print("start_snowballing: starting scraping process on "+q2.database+" (forward query).")
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/snowball_fast.py", "-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:snowball_progress', kwargs={'sbs': sbs.id}))

#########################################################
## Start snowballing
import subprocess
import sys
@login_required
def do_snowballing(request,qid,q2id):

    #ssh_test()

    curdate = timezone.now()

    # Backward query
    # Get current query
    query_b = Query.objects.get(id=qid)

    qtitle  = str.split(query_b.title,"_")[0]
    qtype   = 'backward'
    qstep   = query_b.step
    qdb     = "WoS"
    sbsid   = query_b.snowball

    # Generate query from selected documents
    #TODO: Tag?
    docs    = DocOwnership.objects.filter(query_id=qid, user_id=request.user, relevant=1)
    docdois = []
    for doc in docs:
        docdoi = WoSArticle.objects.get(doc_id=doc.doc_id)
        docdois.append(docdoi.di)
    doiset  = set(docdois)
    if (len(doiset) > 0):
        # Generate query
        qtext   = 'DO = ("' + '" OR "'.join(doiset) + '")'

        print(qtext)

        #  create a new query record in the database
        q_b = Query(
            title=qtitle+"_backward_"+str(qstep+1)+"_1",
            database=qdb,
            type=qtype,
            text=qtext,
            date=curdate,
            snowball=sbsid,
            step=qstep+1,
            substep=1
        )
        q_b.save()

        qid = q_b.id

        # write the query into a text file
        fname = "/queries/"+str(q_b.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

        # run "scrapeQuery.py" on the text file in the background
        p_b = subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

        #return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0, 'q2id': 0}))

    else :
        p_b = subprocess.Popen(["ls"])
        qid = 0
        print("No document to do backward query.")
        #return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': q.id}))


    # Forward query
    # Get current query
    query_f = Query.objects.get(id=q2id)

    qtitle  = str.split(query_f.title,"_")[0]
    qtype   = 'forward'
    qstep   = query_f.step
    qdb     = "WoS"
    sbsid   = query_f.snowball

    # Generate query from selected documents
    #TODO: Tag?
    docs    = DocOwnership.objects.filter(query_id=q2id, user_id=request.user, relevant=1)
    docdois = []
    for doc in docs:
        docdoi = WoSArticle.objects.get(doc_id=doc.doc_id)
        docdois.append(docdoi.di)
    doiset  = set(docdois)
    if (len(doiset) > 0):
        # Generate query
        qtext   = 'DO = ("' + '" OR "'.join(doiset) + '")'

        print(qtext)

        #  create a new query record in the database
        q_f = Query(
            title=qtitle+"_forward_"+str(qstep+1)+"_2",
            database=qdb,
            type=qtype,
            text=qtext,
            date=curdate,
            snowball=sbsid,
            step=qstep+1,
            substep=1
        )
        q_f.save()


        # write the query into a text file
        fname = "/queries/"+str(q_f.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

        # run "scrapeQuery.py" on the text file in the background
        p_f = subprocess.Popen(["python3", "/home/hilj/python_apsis_libs/scrapeWoS/bin/snowball_fast.py","-s", qdb, fname])

        q2id = q_f.id

    else :
        p_f = subprocess.Popen(["ls"])
        q2id = 0
        print("No document to do forward query.")

    exit_codes = [p.wait() for p in [p_b, p_f]]

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': qid, 'substep': 1, 'docadded': 0, 'q2id': q2id}))



#########################################################
## Delete the query
@login_required
def delete_query(request, qid):
    try:
        q = Query.objects.get(pk=qid)
        q.delete()
        title = str(qid.id)
        shutil.rmtree("/queries/"+title)
        os.remove("/queries/"+title+".txt")
        os.remove("/queries/"+title+".log")
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:index'))

#########################################################
## Delete the query
@login_required
def delete_tag(request, qid, tid):
    try:
        t = Tag.objects.get(pk=tid)
        t.delete()
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': qid}))

#########################################################
## Delete the query
@login_required
def delete_sbs(request, sbsid):
    try:
        sbs = SnowballingSession.objects.get(pk=sbsid)

        # Get associated queries
        qs = Query.objects.filter(snowball=sbsid)

        # Delete SB session
        sbs.delete()

        # Delete asociated queries and files
        #TODO: Could be better handled by cascade function in postgres DB
        for qid in qs :
            q = Query.objects.get(pk=qid)
            q.delete()

            title = str(qid)
            shutil.rmtree("/queries/"+title)
            os.remove("/queries/"+title+".txt")
            os.remove("/queries/"+title+".log")
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:snowball'))

#########################################################
## Add the documents to the database
@login_required
def dodocadd(request):
    qid = request.GET.get('qid',None)
    if 'q2id' != 0 or 'q2id' != '0':
        q2id = request.GET.get('q2id',None)
    else:
        q2id = 0
    db  = request.GET.get('db',None)

    q = Query.objects.get(pk=qid)

    if q.dlstat != "NOREC":
        if db=="WoS":
            upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_docs.py'))
        if db=="scopus":
            upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_scopus_docs.py'))

        subprocess.Popen(["python3", upload, qid])

        time.sleep(2)

    if q.type == "default":
        substep = 0
    else:
        substep = 2

    #return HttpResponse(upload)
    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': qid}))

#########################################################
## Page views progress of query scraping
@login_required
def querying(request, qid, substep=0, docadded=0, q2id=0):

    template = loader.get_template('scoping/query_progress.html')

    if 'appmode' not in request.session:
        request.session['appmode'] = "scoping"
    #== SCOPING ===================================================================================
    if request.session['appmode']!='snowballing':

        query = Query.objects.get(pk=qid)

        # How many docs are there already added?
        docs      = Doc.objects.filter(query__id=qid)
        doclength = len(docs)

        if doclength == 0: # if we've already added the docs, we don't need to show the log
            logfile = "/queries/"+str(query.id)+".log"

            wait = True
            # wait up to 15 seconds for the log file, then go to a page which displays its contents
            for i in range(15):
                try:
                    with open(logfile,"r") as lfile:
                        log = lfile.readlines()
                    break
                except:
                    log = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                    time.sleep(1)

            finished = False
            if "done!" in log[-1]:
                finished = True
        else:
            log=False
            finished=True

        context = {
            'log': log,
            'finished': finished,
            'docs': docs,
            'doclength': doclength,
            'query': query,
            'substep': substep
        }

    #== SNOWBALLING ================================================= (all moved down to next fun)
    else:
       context = {}
    return HttpResponse(template.render(context, request))

def snowball_progress(request,sbs):
    template = loader.get_template('scoping/snowball_progress.html')
    do_backward_query = False
    do_forward_query  = False
    stop = False

    sbs = SnowballingSession.objects.get(id=sbs)

    sqs = sbs.query_set.all()

    a = sqs.values()

    seed_query = sqs.get(type='backward',step=1,substep=1)

    # Query 1: Backward / References
    # Check if query is defined
    try:
        query_b = sqs.filter(type='backward').last()
        if query_b.database.lower() == "scopus":
            rfile = "s_results.txt"
        do_backward_query = True

        logfile_b = "/queries/"+str(query_b.id)+".log"
        rstfile_b = "/queries/"+str(query_b.id)+"/"+rfile
        if request.session['DEBUG']:
            print("querying: (backward query) logfile -> "+str(logfile_b)+", result file -> "+str(rstfile_b))
    except:
        query_b = 0

    # Query 2: Forward / Citations
    try:
        query_f = sqs.filter(type='forward').last()
        do_forward_query  = True

        logfile_f = "/queries/"+str(query_f.id)+".log"
        rstfile_f = "/queries/"+str(query_f.id)+"/results.txt"
        if request.session['DEBUG']:
            print("querying: (forward query) logfile -> "+str(logfile_f)+", result file -> "+str(rstfile_f))
    except:
        query_f = 0

    finished   = False
    finished_b = False
    finished_f = False

    request.session['DEBUG'] = False

    if do_backward_query and do_forward_query:
        if request.session['DEBUG']:
            print("querying: Default case with backward query #"+str(query_b.id)+" and forward query #"+str(query_f.id))

        # Check if query result files exist
        if request.session['DEBUG']:
            print("querying: check existence of result files:")
            print("querying:   - backward query rstfile_b -> "+str(os.path.isfile(rstfile_b)))
            print("querying:   - forward query rstfile_f -> "+str(os.path.isfile(rstfile_f)))
        if not os.path.isfile(rstfile_b) and not os.path.isfile(rstfile_f):
            if request.session['DEBUG']:
                print("querying: waiting for query processes to finish.")
            wait = True
            # wait up to 15 seconds for the log file, then go to a page which displays its contents
            for i in range(2):
                try:
                    with open(logfile_b,"r") as lfile:
                        log_b = lfile.readlines()
                    break
                except:
                    log_b = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                    time.sleep(1)

            if query_f.dlstat == "done":
                log_f = ["Citations were all captured in the first substep."]
            else :
                for i in range(2):
                    try:
                        with open(logfile_f,"r") as lfile:
                            log_f = lfile.readlines()
                        break
                    except:
                        log_f = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                        time.sleep(1)

        else:
            if request.session['DEBUG']:
                print("querying: query result files have already been created.")
            with open(logfile_b,"r") as lfile:
                log_b = lfile.readlines()
            with open(logfile_f,"r") as lfile:
                log_f = lfile.readlines()

        ## Check backwards query log for errors or success
        if "couldn't find any records" in log_b[-1]:
            finished_b = True
            query_b.dlstat = "done"
        elif "done!" in log_b[-1]:
            finished_b = True
            query_b.dlstat = "NOREC"
        query_b.save()

        ## Check forwards query log for errors or success
        if "couldn't find any records" in log_f[-1]:
            finished_f = True
            query_f.dlstat = "done"
        elif "done!" in log_f[-1]:
            finished_f = True
            query_f.dlstat = "NOREC"
        query_f.save()

        if request.session['DEBUG']:
            print("querying: finished_b -> "+str(finished_b)+", finished_f -> "+str(finished_f))

        if finished_b == True and finished_f == True:
            finished = True

        # If queries have finished properly then go to next substep directly
        if finished:
            if sqs.count() == 2:
                print("Creating a new query")
                # Create query '2' the next backwards one
                query_b2 = Query(
                    title=str.split(query_b.title, "_")[0]+"_backward_"+str(query_b.step)+"_"+str(query_b.substep+1),
                    database=query_b.database,
                    type="backward",
                    text="",
                    date=timezone.now(),
                    snowball=query_b.snowball,
                    step=query_b.step,
                    substep=query_b.substep+1
                )
                query_b2.save()
                sbs.working = False

        if query_b.text == '':
            branch = Query.objects.get(
                snowball=sbs,step=query_b.step,substep=query_b.substep-1
            )
            log_b = ["Busy checking the references and citations of {} against the database and keywords".format(branch.title)]
            if sbs.working == False:
                background = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','proc_docrefs_scopus.py'))
                subprocess.Popen(["python3", background, str(seed_query.id), str(query_b.id), str(query_f.id)])
                sbs.working = True
                sbs.save()


        if query_b.text !='' and sbs.working == True and os.path.isfile("/queries/"+str(query_b.id)+"/s_results.txt") and query_b.doc_set.all().count() == 0: # if we have scraped all the refs
            log_b = ["Busy checking the references of {} against the database and keywords".format(query_b.title)]
            background = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','proc_docrefs_scopus.py'))
            subprocess.Popen(["python3", background, str(seed_query.id), str(query_b.id), str(0)])
            sbs.working = True
            sbs.save()

        if sbs.working_pb2:
            log_b = ["Busy checking the references of {} against the database and keywords".format(query_b.title)]

        qsum = None
        t = None
        #sqs.filter(type='step_summary').delete()
        if query_b.doc_set.all().count() > 0 and sbs.working==False:
            log_b = ["FINISHED"]
            stop = True
            if sqs.filter(type='step_summary').count() == 0:
                qsum = Query(
                    title=str.split(query_b.title, "_")[0]+"_summary_"+str(query_b.step),
                    database=query_b.database,
                    type="step_summary",
                    text="",
                    date=timezone.now(),
                    snowball=query_b.snowball,
                    step=query_b.step
                )
                qsum.save()
                t = Tag(
                    title = str.split(query_b.title, "_")[0]+"_summary_"+str(query_b.step),
                    text = "",
                    query = qsum
                )
                t.save()
                B2docs = Doc.objects.filter(document__seedquery=seed_query, document__relation=-1,document__indb__gt=0,document__docmatch_q=True).exclude(document__sametech=1)
                F2docs = Doc.objects.filter(document__seedquery=seed_query, document__relation=1,document__indb__gt=0,document__docmatch_q=True)
                C1docs = B2docs | F2docs
                for doc in C1docs:
                    doc.query.add(qsum)
                    doc.tag.add(t)
            else:
                qsum = sqs.filter(type='step_summary').first()
                t = qsum.tag_set.all()[0]


    ## Scrape a query if it needs to be scraped
    if sqs.count() == 3:
        query_b2 = query_b
        if query_b2.text != '': # if the text has been written
            if not os.path.isfile("/queries/"+str(query_b2.id)+"/s_results.txt"): # and there's no file
                log_b = ["Downloading the references from {}".format(query_b2.title)]
                if not sbs.working: # And we're not doing something in the background
                    sbs.working = True
                    sbs.save()
                    fname = "/queries/"+str(query_b2.id)+".txt"
                    with open(fname,encoding='utf-8',mode='w') as qfile:
                        qfile.write(query_b2.text)
                        subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py", "-s", query_b2.database, fname])

    if not do_backward_query or not do_forward_query:
        if request.session['DEBUG']:
            print("querying: No documents to perform backward or forward queries. Going back to snowball home page...")
        return HttpResponseRedirect(reverse('scoping:snowball'))

    drs = DocRel.objects.filter(seedquery=seed_query)

    summary_stats = [
        ('B1', drs.filter(relation=-1,indb=1,sametech=1).count()),
        ('B2', drs.filter(relation=-1,indb__gt=0,docmatch_q=True).exclude(sametech=1).count()),
        ('B3', drs.filter(relation=-1,indb__gt=0,docmatch_q=False).exclude(sametech=1).count()),
        ('B4', drs.filter(relation=-1,indb=0,timatch_q=True).count()),
        ('B5', drs.filter(relation=-1,indb=0,timatch_q=False).count()),
        ('F1', drs.filter(relation=1,indb=1,sametech=1).count()),
        ('F2', drs.filter(relation=1,indb__gt=0,docmatch_q=True).count()),
        ('F3', drs.filter(relation=1,indb__gt=0,docmatch_q=False).count()),
    ]

    # DocRel.objects.filter(seedquery=599,relation=-1,indb=2,docmatch_q=True)

    C2docs = DocRel.objects.filter(seedquery=seed_query,relation=-1,indb=0,timatch_q=True).order_by('au')
    #C2docs = DocRel.objects.filter(seedquery=seed_query,relation=-1,indb=0).order_by('au')

    summary_stats.append(('C1',summary_stats[1][1]+summary_stats[6][1]))
    summary_stats.append(('C2',summary_stats[3][1]))


    fqs = sqs.filter(type='forward')
    for f in fqs:
        f.r_count = f.doc_set.all().count()

    users = User.objects.all().order_by('username')

    proj_users = users.query

    user_list = []

    if qsum is not None:

        for u in users:
            user_docs = {}
            tdocs = DocOwnership.objects.filter(query=qsum,tag=t,user=u)
            print(tdocs)
            user_docs['tdocs'] = tdocs.count()
            if user_docs['tdocs']==0:
                user_docs['tdocs'] = False
            else:
                user_docs['reldocs']         = tdocs.filter(relevant=1).count()
                user_docs['irreldocs']       = tdocs.filter(relevant=2).count()
                user_docs['maybedocs']       = tdocs.filter(relevant=3).count()
                user_docs['yesbuts']         = tdocs.filter(relevant=4).count()
                user_docs['checked_percent'] = round((user_docs['reldocs'] + user_docs['irreldocs'] + user_docs['maybedocs']) / user_docs['tdocs'] * 100)
            if qsum in u.query_set.all():
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

        print(user_list)

    context = {
        'log': True,
        'log_b': log_b,
        'log_f': log_f,
        'doclength': 0,
        'finished': finished,
        'query_b': query_b,
        'query_f': query_f,
        'substep':1,
        'docadded': 0,
        'summary_stats': summary_stats,
        'C2docs': C2docs,
        'fqs': fqs,
        'bqs': sqs.filter(type='backward'),
        'query': qsum,
        'tag': t,
        'users': user_list,
        'stop': stop
    }

    return HttpResponse(template.render(context, request))

############################################################
## SBS - Set default ownership to current user

@login_required
def sbs_allocateDocsToUser(request,qid,q2id):

    DEBUG = False

    #Get queries
    query_b = Query.objects.get(pk=qid)
    query_f = Query.objects.get(pk=q2id)

    if DEBUG:
        print("Getting references query: "+str(query_b.title)+" ("+str(qid)+")")
        print("Getting citations query: " +str(query_f.title)+" ("+str(q2id)+")")

    # Get associated docs
    docs_b = Doc.objects.filter(query=qid)
    docs_f = Doc.objects.filter(query=q2id)

    # Define new tag
    tag_b = Tag(
        title = "sbs_"+str(query_b.title)+"_"+str(request.user),
        text  = "",
        query = query_b
    )
    tag_b.save()
    tag_f = Tag(
        title = "sbs_"+str(query_f.title)+"_"+str(request.user),
        text  = "",
        query = query_f
    )
    tag_f.save()

    # Population Docownership table
    for doc in docs_b:
        docown = DocOwnership(
            doc      = doc,
            user     = request.user,
            query    = query_b,
            tag      = tag_b,
            relevant = 1    # Set all documents to keep status by default
        )
        docown.save()

    for doc in docs_f:
        docown = DocOwnership(
            doc      = doc,
            user     = request.user,
            query    = query_f,
            tag      = tag_f,
            relevant = 1    # Set all documents to keep status by default
        )
        docown.save()

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': query_b.id, 'q2id': query_f.id, 'sbsid': query_b.snowball}))


############################################################
## SBS - Set default ownership to current user

@login_required
def sbs_setAllQDocsToIrrelevant(request,qid,q2id,sbsid):

    DEBUG = True

    #Get query
    query_b = Query.objects.get(pk=qid)
    query_f = Query.objects.get(pk=q2id)

    if DEBUG:
        print("Getting references query: "+str(query_b.title)+" ("+str(qid)+")")
        print("Getting citations query: " +str(query_f.title)+" ("+str(q2id)+")")

    # get latest tag
    tag_b = Tag.objects.filter(query=qid).last()
    tag_f = Tag.objects.filter(query=q2id).last()

    if DEBUG:
        print("Getting references tag: "+str(tag_b.title)+" ("+str(tag_b.text)+")")
        print("Getting citations tag: "+str(tag_f.title)+" ("+str(tag_f.text)+")")

    # Get associated docs
    docs_b = DocOwnership.objects.filter(query=qid, tag=tag_b.id, user=request.user)
    docs_f = DocOwnership.objects.filter(query=q2id, tag=tag_f.id, user=request.user)
    # Population Docownership table
    for doc in docs_b:
        doc.relevant = 2
        doc.save()

    for doc in docs_f:
        doc.relevant = 2
        doc.save()

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

############################################################
## Query homepage - manage tags and user-doc assignments

@login_required
def query(request,qid,q2id='0',sbsid='0'):
    template = loader.get_template('scoping/query.html')

    if 'appmode' not in request.session:
        request.session['appmode'] = "scoping"

    if request.session['appmode'] != "snowballing":

        query = Query.objects.get(pk=qid)

        tags = Tag.objects.filter(query=query)

        tags = tags.values()

        for tag in tags:
            tag['docs']       = Doc.objects.filter(tag=tag['id']).distinct().count()
            tag['a_docs']     = Doc.objects.filter(docownership__tag=tag['id']).distinct().count()
            tag['seen_docs']  = DocOwnership.objects.filter(tag=tag['id'],relevant__gt=0).count()
            tag['rel_docs']   = DocOwnership.objects.filter(tag=tag['id'],relevant=1).count()
            tag['irrel_docs'] = DocOwnership.objects.filter(tag=tag['id'],relevant=2).count()
            try:
                tag['relevance'] = round(tag['rel_docs']/(tag['rel_docs']+tag['irrel_docs'])*100)
            except:
                tag['relevance'] = 0

        fields = ['id','title']

        untagged = Doc.objects.filter(query=query).count() - Doc.objects.filter(query=query,tag__query=query).distinct().count()

        users = User.objects.all()

        proj_users = users.query

        user_list = []

        for u in users:
            user_docs = {}
            tdocs = DocOwnership.objects.filter(query=query,user=u)
            user_docs['tdocs'] = tdocs.count()
            if user_docs['tdocs']==0:
                user_docs['tdocs'] = False
            else:
                user_docs['reldocs']         = tdocs.filter(relevant=1).count()
                user_docs['irreldocs']       = tdocs.filter(relevant=2).count()
                user_docs['maybedocs']       = tdocs.filter(relevant=3).count()
                user_docs['yesbuts']         = tdocs.filter(relevant=4).count()
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
            'users': user_list,
            'user': request.user
        }
    else:
        sbs    = SnowballingSession.objects.get(pk=sbsid)
        query  = Query.objects.get(pk=qid)
        query2 = Query.objects.get(pk=q2id)

        tags = Tag.objects.filter(query=query) | Tag.objects.filter(query=query2)

        tags = tags.values()

        for tag in tags:
            tag['docs']       = Doc.objects.filter(tag=tag['id']).distinct().count()
            tag['a_docs']     = Doc.objects.filter(docownership__tag=tag['id']).distinct().count()
            tag['seen_docs']  = DocOwnership.objects.filter(doc__tag=tag['id'],relevant__gt=0).count()
            tag['rel_docs']   = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=1).count()
            tag['irrel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=2).count()
            try:
                tag['relevance'] = round(tag['rel_docs']/(tag['rel_docs']+tag['irrel_docs'])*100)
            except:
                tag['relevance'] = 0

        fields = ['id','title']

        untagged = Doc.objects.filter(query=query).count() - Doc.objects.filter(query=query,tag__query=query).distinct().count() + Doc.objects.filter(query=query2).count() - Doc.objects.filter(query=query2,tag__query=query2).distinct().count()

        users = User.objects.all()

        proj_users = users.query

        user_list = []

        for u in users:
            user_docs = {}
            tdocs = DocOwnership.objects.filter(query=query,user=u) | DocOwnership.objects.filter(query=query2,user=u)
            user_docs['tdocs'] = tdocs.count()
            if user_docs['tdocs']==0:
                user_docs['tdocs'] = False
            else:
                user_docs['reldocs']         = tdocs.filter(relevant=1).count()
                user_docs['irreldocs']       = tdocs.filter(relevant=2).count()
                user_docs['checked_percent'] = round((user_docs['reldocs'] + user_docs['irreldocs']) / user_docs['tdocs'] * 100)
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
            'sbs': sbs,
            'query': query,
            'query2': query2,
            'tags': list(tags),
            'fields': fields,
            'untagged': untagged,
            'users': user_list,
            'user': request.user
        }


    return HttpResponse(template.render(context, request))

##################################################
## User home page

@login_required
def userpage(request):
    template = loader.get_template('scoping/user.html')

    # Queries
    queries = Tag.objects.filter(query__users=request.user).values('query__id','query__type','id')

    query_list = []

    for qt in queries:
        q = Query.objects.get(pk=qt['query__id'])
        tag = Tag.objects.get(pk=qt['id'])
        ndocs           = Doc.objects.filter(query=q).count()
        dos = DocOwnership.objects.filter(query=q,user=request.user,tag=tag)
        revdocs         = dos.count()
        reviewed_docs   = dos.filter(relevant__gt=0).count()
        unreviewed_docs = revdocs - reviewed_docs
        reldocs   = dos.filter(relevant=1).count()
        irreldocs = dos.filter(relevant=2).count()
        maybedocs = dos.filter(relevant=3).count()
        yesbuts   = dos.filter(relevant=4).count()
        try:
            relevance = round(reldocs/(reldocs+irreldocs)*100)
        except:
            relevance = 0
        if revdocs > 0:
            query_list.append({
                'id': q.id,
                'tag': tag,
                'type': q.type,
                'title': q.title,
                'ndocs': ndocs,
                'revdocs': revdocs,
                'revieweddocs': reviewed_docs,
                'unreviewed_docs': unreviewed_docs,
                'reldocs': reldocs,
                'maybedocs': maybedocs,
                'yesbuts': yesbuts,
                'relevance': relevance,
                'reldocs': reldocs,
                'irreldocs': irreldocs
            })

    query = queries.last()


    # Snowballing sesseions
   # sb_sessions     = SnowballingSession.objects.all().order_by('-id')

    # Get latest step associated with each SB sessions
    # Initialise variable that will contain the information to be sent to the webpage (context)
    #sb_info = []

    # Loop over SB sessions
    #for sbs in sb_sessions:
    #    sb_info_tmp = {}
    #    sb_info_tmp['id']     = sbs.id
    #    sb_info_tmp['name']   = sbs.name
    #    sb_info_tmp['ip']     = sbs.initial_pearls
    #    sb_info_tmp['date']   = sbs.date
    #    sb_info_tmp['status'] = sbs.status

        # Get queries associated with the current SB session
    #    sb_qs    = Query.objects.filter(snowball = sbs.id).order_by('-id')

        # Initialise step, count and query_info variables
    #    step     = "1"
    #    nbdocsel = 0
    #    nbdoctot = 0
    #    nbdocrem = 0
    #    sb_info_tmp['q_info'] = []

        # Loop over queries associated with the current SB session
    #    cnt = 0 # Query iterator to capture last query (There must be a better way to do that)
    #    for q in sb_qs:
            # Select reference queries only (sub-step == 2)
    #        if q.title.split("_")[3] == "2":
                # For old queries
    #            try:
    #                q_info_tmp             = {}
    #                q_info_tmp['id']       = q.id
    #                q_info_tmp['title']    = q.title
    #                q_info_tmp['type']     = q.type
                    #q_info_tmp['nbdoctot'] = DocOwnership.objects.filter(query = q, user=request.user).count()
                    #q_info_tmp['nbdocsel'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                    #q_info_tmp['nbdocrev'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 0).count()
                    #q_info_tmp['nbdoctot'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
    #                q_info_tmp['nbdocsel'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
    #                q_info_tmp['nbdocrem'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()
    #                q_info_tmp['nbdoctot'] = q_info_tmp['nbdocsel'] + q_info_tmp['nbdocrem']

    #                if cnt == 0:
    #                    q_info_tmp['last'] = "True"
    #                else:
    #                    q_info_tmp['last'] = "False"##
#
#                    sb_info_tmp['q_info'].append(q_info_tmp)
#                except:
#                    q_info_tmp             = {}
#                    q_info_tmp['id']       = q.id
#                    q_info_tmp['title']    = q.title
#                    q_info_tmp['type']     = q.type
                    #q_info_tmp['nbdoctot'] = DocOwnership.objects.filter(query = q, user=request.user).count()
                    #q_info_tmp['nbdocsel'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                    #q_info_tmp['nbdocrev'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 0).count()
#                    q_info_tmp['nbdoctot'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
#                    q_info_tmp['nbdocsel'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
#                    q_info_tmp['nbdocrem'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()

#                    if cnt == 0:
#                        q_info_tmp['last'] = "True"
#                    else:
#                        q_info_tmp['last'] = "False"

   #                 sb_info_tmp['q_info'].append(q_info_tmp)

                # Get current step
#                s = q.title.split("_")[2]
#                if s > step:
#                    step = s

                # Update total counts
                #nbdoctot += DocOwnership.objects.filter(query = q, user=request.user).count()
                #nbdocsel += DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                #nbdocrev += DocOwnership.objects.filter(query = q, user=request.user, relevant = 2).count()
                #nbdoctot += Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
 #               nbdocsel += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
 #               nbdocrem += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()
 #               nbdoctot += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count() + Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()

                # Update iterator
  #              cnt += 1

        # Update info of current SB session
   #     sb_info_tmp['ns']    = step
    #    sb_info_tmp['lq']    = sb_qs.last().id
    #    sb_info_tmp['rc']    = sb_qs.last().r_count
    #    sb_info_tmp['ndsel'] = str(nbdocsel)
    #    sb_info_tmp['ndtot'] = str(nbdoctot)
    #    sb_info_tmp['ndrem'] = str(nbdocrem)

        # Add SB session info to container
     #   sb_info.append(sb_info_tmp)


    context = {
        'user': request.user,
        'queries': query_list,
        'query': query
#        'sbsessions': sb_info
    }
    return HttpResponse(template.render(context, request))

##################################################
## Exclude docs from snowballing session
@login_required
def sbsKeepDoc(request,qid,did):

    #Set doc review to 0
    docs = DocOwnership.objects.all(doc=did, query=qid, user=request.user)

    print(docs)


    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

##################################################
## Exclude docs from snowballing session
@login_required
def sbsExcludeDoc(request,qid,did):

    #Set doc review to 0
    docs = DocOwnership.objects.all(doc=did, query=qid, user=request.user)

    print(docs)


    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

##################################################
## View all docs
@login_required
def doclist(request,qid,q2id='0',sbsid='0'):

    template = loader.get_template('scoping/docs.html')

    print(str(qid))
    print(str(q2id))

    if qid == 0 or qid=='0':
        qid = Query.objects.all().last().id

    query = Query.objects.get(pk=qid)
    qdocs = Doc.objects.filter(query__id=qid)

    if q2id != '0' and sbsid != '0':
        #TODO: Select categories B2, B4 and F2
        query_b = Query.objects.get(pk=qid)
        query_f = Query.objects.get(pk=q2id)
        qdocs_b = Doc.objects.filter(query__id=qid)
        qdocs_f = Doc.objects.filter(query__id=q2id)
        all_docs = qdocs_b | qdocs_f
    else:
        query_f  = False
        all_docs = qdocs

    ndocs = all_docs.count()

    docs = list(all_docs[:500].values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))


    fields = []
    basic_fields = []
    author_fields = []
    relevance_fields = []
    wos_fields = []
    basic_field_names = ['Title', 'Abstract', 'Year'] #, str(request.user)]

    relevance_fields.append({"path": "tech_technology", "name": "Technology"})
    relevance_fields.append({"path": "tech_innovation", "name": "Innovation"})
    relevance_fields.append({"path": "relevance_netrelevant", "name": "NETs relevant"})
    relevance_fields.append({"path": "relevance_techrelevant", "name": "Technology relevant"})
    relevance_fields.append({"path": "note__text", "name": "Notes"})

    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name

        if f.verbose_name in basic_field_names:
            print(f.name)
            basic_fields.append({"path": path, "name": f.verbose_name})
        fields.append({"path": path, "name": f.verbose_name})
        wos_fields.append({"path": path, "name": f.verbose_name})

    for u in User.objects.all():
        path = "docownership__"+u.username
        fields.append({"path": path, "name": u.username})
        relevance_fields.append({"path": path, "name": u.username})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query" and f.name!="id":
            fields.append({"path": path, "name": f.verbose_name})
            author_fields.append({"path": path, "name": f.verbose_name})

    fields.append({"path": "tag__title", "name": "Tag name"})
    relevance_fields.append({"path": "tag__title", "name": "Tag name"})





    context = {
        'query': query,
        'query2' : query_f,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'author_fields': author_fields,
        'relevance_fields': relevance_fields,
        'wos_fields': wos_fields,
        'ndocs': ndocs,
        'sbsid': sbsid,
        'basic_field_names': basic_field_names
    }
    return HttpResponse(template.render(context, request))



###########################################################
## List documents related to a Snowballing session
@login_required
def docrellist(request,sbsid,qid=0,q2id=0,q3id=0):

    request.session['appmode'] == "snowballing"

    template = loader.get_template('scoping/docrels.html')

    # Get snowballing session info
    sbs = SnowballingSession.objects.get(pk=sbsid)

    # Get the backward and forward queries associated with the the current SBS
    if qid == 0 or qid == '0':
        query_b1 = Query.objects.filter(type="backward", snowball=sbs.id, substep=1).last()
    else:
        query_b1 = Query.objects.get(pk=qid)
    if q2id == 0 or q2id == '0':
        query_b2 = Query.objects.filter(type="backward", snowball=sbs.id, substep=2).last()
    else:
        query_b2 = Query.objects.get(pk=q2id)
    if q3id == 0 or q3id == '0':
        query_f = Query.objects.filter(type="forward", snowball=sbs.id).last()
    else:
        query_f = Query.objects.get(pk=q3id)

    # Get all document relationships
    docrels = DocRel.objects.filter(seedquery=query_b1).order_by("relation")
    print(docrels.values("relation")[400:406])

    docs = []
    count = {}
    count['TOTAL'] = 0
    count['category1']  = 0
    count['category2']  = 0
    count['optional']  = 0
    count['discarded']  = 0
    count['B1']  = 0
    count['B2']  = 0
    count['B3']  = 0
    count['B4']  = 0
    count['B5']  = 0
    count['F1']  = 0
    count['F2']  = 0
    count['F3']  = 0

    for dr in docrels:
        count['TOTAL'] += 1
        if "a" == "a":
            tmp = {}
            tmp['title']      = dr.title
            tmp['author']     = dr.au
            tmp['py']         = dr.PY
            tmp['doi']        = dr.doi
            tmp['hasdoi']     = dr.hasdoi
            tmp['docmatch_q'] = dr.docmatch_q
            tmp['timatch_q']  = dr.timatch_q
            tmp['indb']       = dr.indb
            tmp['sametech']   = dr.sametech
            if dr.relation == -1:
                tmp['querytype']  = 'B'
            if dr.relation == 1:
                tmp['querytype']  = 'F'
            if dr.relation == 0:
                tmp['querytype']  = 'Undef'

            # Specific document category
            if (dr.relation == -1 and dr.indb == 1 and dr.sametech == 1):
                tmp['category'] = "B1"
                tmp['user_category'] = "optional"
                count['B1']  += 1
                count['optional'] += 1
            if (dr.relation == -1 and dr.indb == 1 and dr.sametech != 1 and dr.docmatch_q):
                tmp['category'] = "B2"
                tmp['user_category'] = "Category 1"
                count['B2']  += 1
                count['category1'] += 1
            if (dr.relation == -1 and dr.indb == 1 and dr.sametech != 1 and not dr.docmatch_q):
                tmp['category'] = "B3"
                tmp['user_category'] = "discarded"
                count['B3']  += 1
                count['discarded'] += 1
            if (dr.relation == -1 and dr.indb == 2 and dr.docmatch_q):
                tmp['category'] = "B4"
                tmp['user_category'] = "Category 2"
                count['B4']  += 1
                count['category2'] += 1
            if (dr.relation == -1 and dr.indb == 2 and not dr.docmatch_q):
                tmp['category'] = "B5"
                tmp['user_category'] = "discarded"
                count['B5']  += 1
                count['discarded'] += 1
            if (dr.relation == 1 and dr.indb == 1 and dr.sametech == 1 ):
                tmp['category'] = "F1"
                tmp['user_category'] = "optional"
                count['F1']  += 1
                count['optional'] += 1
            if (dr.relation == 1 and dr.indb > 0 and dr.docmatch_q):
                tmp['category'] = "F2"
                tmp['user_category'] = "Category 1"
                count['F2']  += 1
                count['category1'] += 1
            if (dr.relation == 1 and dr.indb > 0 and not dr.docmatch_q):
                tmp['category'] = "F3"
                tmp['user_category'] = "discarded"
                count['F3']  += 1
                count['discarded'] += 1

            # Get abstract when possible
            try:
                d = dr.referent
                tmp['abstract']   = d.content[0:10]
            except:
                tmp['abstract']   = "None"
            #tmp['abstract']   = "None"

            # Get document relevance when possible
            try:
                r = DocOwnership.objects.get(doc = dr.referent)
                tmp['relevant']   = r.relevant
            except:
                tmp['relevant']   = "NA"

            docs.append(tmp)
        else:
            print("you should not be there...")

    context = {
        'docs': docs,
        'count': count,
        'sbsid': sbsid,
        'query_b1': query_b1,
        'query_b2': query_b2,
        'query_f': query_f
    }

    return HttpResponse(template.render(context, request))


###########################################################
## Manual docadd form
def add_doc_form(request,qid=0,authtoken=0):
    try:
        query = Query.objects.get(pk=qid)
    except:
        query = Query.objects.last()
    if authtoken!=0:
        em = EmailTokens.objects.get(pk=authtoken)
        em.sname, em.initial = em.AU.split(',')

        template = loader.get_template('scoping/ext_doc_add.html')
    else:
        em = None
        template = loader.get_template('scoping/doc_add.html')



    basic_fields = [
        {"path": "UT", "name": "Url", "ab": "UT","note": "This is used to uniquely identify the document"},
        {"path": "title", "name": "Title", "ab": "TI", "note": "Enter the document's title"},
        {"path": "PY", "name": "Publishing Year", "ab": "PY", "note": "Enter the year the document was published"},
        {"path": "content", "name": "Abstract", "ab": "AB","note": "Enter the abstract of the document, or if it does not have an abstract, the first paragraph"},
    ]

    author_fields = []
    for a in range(1,11):
        author_fields.append({"path": "author__"+str(a), "name": "Author "+str(a)})

    fields = []
    if em is None:
        for f in WoSArticle._meta.get_fields():
            path = "wosarticle__"+f.name
            if f.name !="doc" and f.name.upper() not in [x['ab'] for x in basic_fields]:
                fields.append({"path": path, "name": f.verbose_name, "ab": f.name.upper()})

    context = {
        'fields': fields,
        'query': query,
        'basic_fields': basic_fields,
        'author_fields': author_fields,
        'techs': Technology.objects.all(),
        'em': em
    }
    return HttpResponse(template.render(context, request))

## Manual docadd form HANDLER
def do_add_doc(request):

    d = request.POST

    t = Technology.objects.get(pk=d['technology'])

    # create new query
    q = Query(
        title="Manual add "+d['title'],
        type="default",
        text="Manually add "+d['title']+" at "+str(timezone.now()),
        creator = request.user,
        date = timezone.now(),
        database = "manual",
        r_count = 1,
        technology=t
    )
    q.save()

    Doc.objects.get(UT=d['UT']).delete()

    # create new doc
    doc = Doc(UT=d['UT'])

    doc.UT=d['UT']
    doc.title=d['title']
    doc.PY=d['PY']
    doc.content=d['content']

    doc.save()

    # Add doc to query
    doc.query.add(q)

    article = WoSArticle(
        doc=doc
    )

    article.ti=d['title']
    article.py=d['PY']
    article.ab=d['content']

    pos = 0
    for f in d:
        # create new docauthors
        if "author__" in f:
            if len(d[f].strip()) > 0 :
                pos+=1
                if DocAuthInst.objects.filter(doc=doc,position=pos).count() == 1:
                    dai = DocAuthInst.objects.get(doc=doc,position=pos)
                else:
                    dai = DocAuthInst(doc=doc)
                dai.AU = d[f].strip()
                dai.position = pos
                dai.save()
        # populate new wosarticle
        if "wosarticle__" in f:
            if len(d[f].strip()) > 0 :
                fn = f.split('__')[1]
                setattr(article,fn,d[f])

    article.save()

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': q.id}))


from django.db.models.aggregates import Aggregate
# class StringAgg(Aggregate):
#     function = 'STRING_AGG'
#     template = "%(function)s(%(expressions)s, '%(delimiter)s')"
#
#     def __init__(self, expression, delimiter, **extra):
#         super(StringAgg, self).__init__(expression, delimiter=delimiter, **extra)
#
#     def convert_value(self, value, expression, connection, context):
#         if not value:
#             return ''
#         return value

from django.contrib.postgres.aggregates import StringAgg


##################################################
## View all docs in a Snowball session
@login_required
def doclistsbs(request,sbsid):

    template = loader.get_template('scoping/docs_sbs.html')

    print(str(sbsid))

    if sbsid == 0 or sbsid=='0':
        sbsid = SnowballingSession.objects.all().last().id

    sbs = SnowballingSession.objects.get(pk=sbsid)

    all_docs = []
    queries = Query.objects.filter(snowball=sbsid)

    # Loop over queries
    for q in queries:
        # Filter out non-reference queries
        tmp = str.split(q.title,"_")
        if tmp[len(tmp)-1] == "2":
            qdocs    = Doc.objects.filter(query__id=400,docownership__relevant=1,docownership__query=400)
            #all_docs.append(qdocs.values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))
            qdocs2 = qdocs.values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py')
            for d in qdocs2:
                all_docs.append(d)

    print(type(all_docs))
    print(all_docs)

    ndocs = len(all_docs)

    print(ndocs)

    docs = all_docs
    #docs = list(all_docs[:100].values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))

    print(len(docs))
    print(docs)


    fields = []

   # for f in Doc._meta.get_fields():
   #     if f.is_relation:
   #         for rf in f.related_model._meta.get_fields():
   #             if not rf.is_relation:
   #                 path = f.name+"__"+rf.name
   #                 fields.append({"path": path, "name": rf.verbose_name})
    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name
        if f.name !="doc":
            fields.append({"path": path, "name": f.verbose_name})

   # for f in DocOwnership._meta.get_fields():
   #     if f.name == "user":
   #         path = "docownership__user__username"
   #     else:
   #         path = "docownership__"+f.name
   #     if f.name !="doc" and f.name !="query":
   #         fields.append({"path": path, "name": f.verbose_name})

    for u in User.objects.all():
        path = "docownership__"+u.username
        fields.append({"path": path, "name": u.username})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query":
            fields.append({"path": path, "name": f.verbose_name})

    fields.append({"path": "tag__title", "name": "Tag name"})

    basic_fields = ['Title', 'Abstract', 'Year'] #, str(request.user)]

    context = {
        'sbs': sbs,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'ndocs': ndocs,
    }
    return HttpResponse(template.render(context, request))



##################################################
## Ajax function, to return sorted docs

@login_required
def sortdocs(request):

    qid  = request.GET.get('qid',None)
    q2id = request.GET.get('q2id',None)
    fields = request.GET.getlist('fields[]',None)
    field = request.GET.get('field',None)
    sortdir = request.GET.get('sortdir',None)
    extra_field = request.GET.get('extra_field',None)

    f_fields = request.GET.getlist('f_fields[]',None)
    f_operators = request.GET.getlist('f_operators[]',None)
    f_text = request.GET.getlist('f_text[]',None)
    f_join = request.GET.getlist('f_join[]',None)

    sort_dirs = request.GET.getlist('sort_dirs[]',None)
    sort_fields = request.GET.getlist('sort_fields[]',None)

    tag_title = request.GET.get('tag_title',None)
    download = request.GET.get('download',None)

    # get the query
    query = Query.objects.get(pk=qid)

    # filter the docs according to the query
    if q2id != '0':
        query_f = Query.objects.get(pk=q2id)
        qdocs_f = Doc.objects.filter(query__id=q2id)
        all_docs = Doc.objects.filter(query__id=qid) | qdocs_f
        filt_docs = Doc.objects.filter(query__id=qid) | qdocs_f
    else:
        query_f  = False
        all_docs = Doc.objects.filter(query__id=qid).values_list('UT',flat=True)
        filt_docs = Doc.objects.filter(UT__in=all_docs)

    #if "tag__title" in fields:
    #    filt_docs = filt_docs.filter(tag__query__id=qid)

    fields = tuple(fields)

    single_fields = ['UT']
    mult_fields = []
    users = []
    rfields = []
    for f in fields:
        if "docauthinst" in f or "tag__" in f:
            mult_fields.append(f)
            #single_fields.append(f)
        elif "docownership" in f:
            users.append(f)
        elif "relevance_" in f or "note_" in f:
            rfields.append(f)
            single_fields.append(f)
        else:
            single_fields.append(f)
    single_fields = tuple(single_fields)
    mult_fields_tuple = tuple(mult_fields)

    tech = query.technology
    print(len(filt_docs))
    # annotate with relevance
    if "relevance_netrelevant" in rfields:
        filt_docs = filt_docs.annotate(relevance_netrelevant=models.Sum(
            models.Case(
                models.When(docownership__relevant=1,then=1),
                default=0,
                output_field=models.IntegerField()
            )
        ))
    if "relevance_techrelevant" in rfields:
        filt_docs = filt_docs.annotate(relevance_techrelevant=models.Sum(
            models.Case(
                models.When(docownership__relevant=1,docownership__query__technology=tech,then=1),
                default=0,
                output_field=models.IntegerField()
            )
        ))

    # Annotate with technology names
    if "tech_technology" in fields:
        filt_docs = filt_docs.annotate(
            qtechnology=StringAgg('query__technology__name','; ',distinct=True),
            dtechnology=StringAgg('technology__name','; ',distinct=True),
            #tech_technology=Concat(F('qtechnology'), F('dtechnology'))
        )
        filt_docs = filt_docs.annotate(
            tech_technology=Concat('qtechnology', 'dtechnology')
        )
    # Annotate with innovation names
    if "tech_innovation" in fields:
        filt_docs = filt_docs.annotate(
            qtechnology=StringAgg('query__innovation__name','; ',distinct=True),
            dtechnology=StringAgg('innovation__name','; ',distinct=True),
            #tech_technology=Concat(F('qtechnology'), F('dtechnology'))
        )
        filt_docs = filt_docs.annotate(
            tech_innovation=Concat('qtechnology', 'dtechnology')
        )
    #x = y

    print(len(filt_docs))
    # filter documents with user ratings
    if len(users) > 0:
        uname = users[0].split("__")[1]
        user = User.objects.get(username=uname)
        null_filter = 'docownership__relevant__isnull'
        if q2id!='0':
            reldocs = filt_docs.filter(docownership__user=user,docownership__query=query) | filt_docs.filter(docownership__user=user,docownership__query=query_f)
            if "tag__title" in f_fields:
                reldocs = filt_docs.filter(docownership__user=user,docownership__query=query, docownership__tag__title__icontains=tag_filter) | filt_docs.filter(docownership__user=user,docownership__query=query_f, docownership__tag__title__icontains=tag_filter)
                print(reldocs)
            reldocs = reldocs.values("UT")
            filt_docs = filt_docs.filter(UT__in=reldocs)
        else:
            reldocs = filt_docs.filter(docownership__user=user,docownership__query=query)
            if "tag__title" in f_fields:
                reldocs = filt_docs.filter(docownership__user=user,docownership__query=query, docownership__tag__title__icontains=tag_filter)
                print(reldocs)
            reldocs = reldocs.values("UT")
            filt_docs = filt_docs.filter(UT__in=reldocs)
        for u in users:
            uname = u.split("__")[1]
            user = User.objects.get(username=uname)
            #uval = reldocs.filter(docownership__user=user).docownership
            filt_docs = filt_docs.filter(docownership__user=user,docownership__query=query).annotate(**{
                u: models.Case(
                        models.When(docownership__user=user,docownership__query=query,then='docownership__relevant'),
                        default=0,
                        output_field=models.IntegerField()
                )
            })


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
        if f_operators[i] == "notexact":
            op = "exact"
            exclude = True
        else:
            op =  f_operators[i]
            exclude = False
        try:
            if "tag__title" in f_fields[i]:
                if q2id != '0':
                    filt_docs = filt_docs.filter(tag__query__id=qid,tag__title__icontains=f_text[i]) | filt_docs.filter(tag__query__id=q2id,tag__title__icontains=f_text[i])
                else:
                    filt_docs = filt_docs.filter(tag__query__id=qid,tag__title__icontains=f_text[i])
                tag_filter = f_text[i]
            else:
                if "docownership__" in f_fields[i]:
                    f_text[i] = getattr(DocOwnership,f_text[i].upper())
                    print(f_text[i])
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
                        filt_docs = filt_docs | all_docs.filter(**kwargs)
                tag_text+= '{0} {1} {2} {3}'.format(text_joiner, f_fields[i], f_operators[i], f_text[i])
        except:
            break

    print(len(filt_docs))


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



    #print(len(filt_docs))

    if sort_dirs is not None:
        order_by = ('-PY','UT')
        if len(sort_dirs) > 0:
            order_by = []
        for s in range(len(sort_dirs)):
            sortdir = sort_dirs[s]
            field = sort_fields[s]
            if sortdir=="+":
                sortdir=""
            null_filter = field+'__isnull'
            order_by.append(sortdir+field)
            filt_docs = filt_docs.filter(**{null_filter:False})
        #print(order_by) COMMENTED BECAUSE OF 500 ERROR
        if download != "true":
            docs = filt_docs.order_by(*order_by).values(*single_fields)[:100]
        else:
            docs = filt_docs.order_by(*order_by).values(*single_fields)


        if len(mult_fields) > 0:

            for d in docs:
                for m in range(len(mult_fields)):
                    f = (mult_fields_tuple[m],)
                    if "tag__" in mult_fields_tuple[m]:
                        if q2id!='0':
                            adoc = Tag.objects.all().filter(doc__UT=d['UT'],query=qid).values_list("title") | Tag.objects.all().filter(doc__UT=d['UT'],query=q2id).values_list("title")
                        else:
                            adoc = Tag.objects.all().filter(doc__UT=d['UT'],query=qid).values_list("title")
                    else:
                        adoc = filt_docs.filter(UT=d['UT']).values_list(*f).order_by('docauthinst__position')
                    d[mult_fields[m]] = "; <br>".join(str(x) for x in (list(itertools.chain(*adoc))))

    for d in docs:
        # work out total relevance
        if "relevance__netrelevantasdfasdf" in rfields:
            d["relevance__netrelevant"] = DocOwnership.objects.filter(doc_id=d['UT'],relevant__gt=0).count()
        # Get the user relevance rating for each doc (if asked)
        if len(users) > 0:
            for u in users:
                uname = u.split("__")[1]
                #print(uname)
                doc = Doc.objects.get(UT=d['UT'])
                #print(d['UT'])
                if q2id!='0':
                    do = DocOwnership.objects.filter(doc_id=d['UT'],query__id=qid,user__username=uname) | DocOwnership.objects.filter(doc_id=d['UT'],query__id=q2id,user__username=uname)
                else:
                    do = DocOwnership.objects.filter(doc_id=d['UT'],query__id=qid,user__username=uname)
                if "tag__title" in f_fields:
                    do = do.filter(tag__title__icontains=tag_filter)
                if do.count() > 0:
                    d[u] = do.first().relevant
                    text = do.first().get_relevant_display()
                    tag = str(do.first().tag.id)
                    user = str(User.objects.filter(username=uname).first().id)
                    if download == "false":
                        d[u] = '<span class="relevant_cycle" data-user='+user+' data-tag='+tag+' data-id='+d['UT']+' data-value='+str(d[u])+' onclick="cyclescore(this)">'+text+'</span>'
        try:
            d['wosarticle__di'] = '<a target="_blank" href="http://dx.doi.org/'+d['wosarticle__di']+'">'+d['wosarticle__di']+'</a>'
        except:
            pass

    if download == "true":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="documents.csv"'

        writer = csv.writer(response)

        writer.writerow(fields)

        for d in docs:
            row = [d[x] for x in fields]
            writer.writerow(row)

        return response

    #x = zu
    response = {
        'data': list(docs),
        'n_docs': filt_docs.count()
    }

    template = loader.get_template('scoping/doc.html')
    context = {

    }
    #return HttpResponse(template.render(context, request))

    #x = y
    return JsonResponse(response,safe=False)


def get_tech_docs(tid,other=False):
    if tid=='0':
        tech = Technology.objects.all().values('id')
        tobj = Technology(pk=0,name="NETS: All Technologies")
    else:
        tech = Technology.objects.filter(pk=tid).values('id')
        tobj = Technology.objects.get(pk=tid)
    docs1 = list(Doc.objects.filter(
        query__technology__in=tech,
        query__type="default"
    ).values_list('UT',flat=True))
    docs2 = list(Doc.objects.filter(
        technology__in=tech
    ).values_list('UT',flat=True))
    dids = list(set(docs2)|set(docs1))
    docs = Doc.objects.filter(UT__in=dids)
    nqdocs = Doc.objects.filter(UT__in=docs2).exclude(UT__in=docs1)

    if other:
        return [tech,docs,tobj,nqdocs]
    else:
        return [tech,docs,tobj]

from collections import defaultdict

def technology(request,tid):
    template = loader.get_template('scoping/technology.html')
    tech, docs, tobj, nqdocs = get_tech_docs(tid,other=True)
    docinfo={}
    docinfo['nqdocs'] = nqdocs.distinct('UT').count()
    docinfo['tdocs'] = docs.distinct('UT').count()
    docinfo['reldocs'] = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech
    ).distinct('UT').count() + nqdocs.distinct('UT').count()

    docs = docs.order_by('PY').filter(PY__gt=1985)

    rdocids = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech
    ).values_list('UT',flat=True)

    rdocids = list(rdocids)

    rdocs = docs.filter(UT__in=rdocids).values('PY').annotate(
        n=models.Count("UT"),
        relevant=models.Value("Relevant", models.TextField())
    )
    nrdocs = docs.exclude(UT__in=rdocids).values('PY').annotate(
        n=models.Count("UT"),
        relevant=models.Value("Not Relevant", models.TextField())
    )

    all = list(nrdocs)+list(rdocs)
    docjson = json.dumps(all)

    docjson2 = []

    d = defaultdict(dict)
    for l in (rdocs,nrdocs):
        for elem in l:
            d[elem['PY']].update(elem)


    #bypy = docs.values('PY','techrelevant').annotate(
    #    n=models.Count("UT")
    #)

    context = {
        'tech': tobj,
        'docinfo': docinfo,
        'bypy': docjson,
        'nqdocs': nqdocs
        #'bypy': list(bypy.values('PY','techrelevant','n'))
    }

    return HttpResponse(template.render(context, request))

def download_tdocs(request,tid):
    tech, docs, tobj, nqdocs = get_tech_docs(tid,other=True)
    rdocs = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech
    )
    trdocs = docs.filter(technology__in=tech)
    rdocs = rdocs | trdocs
    rdocs = rdocs.distinct('UT')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="documents.csv"'

    writer = csv.writer(response)

    writer.writerow(['UT','PY','CITATION'])

    for d in rdocs.iterator():
        row = [d.UT,d.PY,d.citation()]
        writer.writerow(row)

    return response

def prepare_authorlist(request,tid):
    tech, docs, tobj = get_tech_docs(tid)
    docs = docs.filter(
        docownership__relevant=1,
        docownership__query__technology__in=tech
    )
    docids = docs.values_list('UT',flat=True)

    emails = Doc.objects.filter(UT__in=docids,wosarticle__em__isnull=False).annotate(
        em_lower=Func(F('wosarticle__em'), function='lower')
    ).distinct('em_lower')#.values('em_lower').distinct()

    ems = []
    em_values = []
    for d in emails.iterator():
        #d = Doc.objects.filter(wosarticle__em__icontains=em['em_lower']).first()
        if d.wosarticle.em is not None:
            evalue = d.wosarticle.em.split(';')[0]
            if evalue not in em_values:
                au = d.docauthinst_set.order_by('position').first()
                audocs = docs.filter(docauthinst__AU=au)
                docset = "; ".join([x.citation() for x in audocs])
                et, created = EmailTokens.objects.get_or_create(email=evalue,AU=au)
                link = 'https://apsis.mcc-berlin.net/scoping/external_add/{}'.format(et.id)
                ems.append({
                    "name": au.AU,
                    "email": evalue,
                    "docset": docset,
                    "link": link
                })
                em_values.append(evalue)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="email_list.csv"'

    writer = csv.writer(response, delimiter=';')

    writer.writerow(["name","email","docset","link"])

    print(ems)

    for em in ems:
        writer.writerow([em["name"],em["email"],em["docset"],em["link"]])

    return response

def document(request,doc_id):
    template = loader.get_template('scoping/document.html')
    doc = Doc.objects.get(pk=doc_id)
    authors = DocAuthInst.objects.filter(doc=doc)
    queries = Query.objects.filter(doc=doc)
    technologies = doc.technology.all()
    innovations = doc.innovation.all()
    ratings = doc.docownership_set.all()
    if request.user.username in ["galm","roger","nemet"]:
        extended=True
    else:
        extended=False
    context = {
        'doc': doc,
        'authors': authors,
        'technologies': technologies,
        'innovations': innovations,
        'ratings': ratings,
        'queries': queries,
        'extended': extended
    }
    return HttpResponse(template.render(context, request))

def cycle_score(request):

    qid = int(request.GET.get('qid',None))
    q2id = int(request.GET.get('q2id',None))
    score = int(request.GET.get('score',None))
    doc_id = request.GET.get('doc_id',None)
    user = int(request.GET.get('user',None))
    tag = int(request.GET.get('tag',None))

    query = Query.objects.get(id=qid)

    if query.type == "default":
        if score == 4:
            new_score = 0
        else:
            new_score = score+1
        docown = DocOwnership.objects.filter(query__id=qid, doc__UT=doc_id, user__id=user, tag__id=tag).first()
        docown.relevant = new_score
        docown.save()
    else:
        query2 = Query.objects.get(id=q2id)
        if score == 2:
            new_score = 1
        else:
            new_score = score+1

        # Check
        docown = DocOwnership.objects.filter(query__id=qid, doc__UT=doc_id, user__id=user, tag__id=tag).first()
        if (docown == None):
            docown = DocOwnership.objects.filter(query__id=q2id, doc__UT=doc_id, user__id=user, tag__id=tag).first()

        docown.relevant = new_score
        docown.save()

    return HttpResponse("")

@login_required
@user_passes_test(lambda u: u.is_superuser)
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

def update_criteria(request):
    qid = request.GET.get('qid',None)
    criteria = request.POST['criteria']

    query = Query.objects.get(pk=qid)
    query.criteria = criteria
    query.save()

    return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': qid}))

def assign_docs(request):
    qid = request.GET.get('qid',None)
    users = request.GET.getlist('users[]',None)
    tags = request.GET.getlist('tags[]',None)
    tagdocs = request.GET.getlist('tagdocs[]',None)
    docsplit = request.GET.get('docsplit',None)

    #print(docsplit)

    query = Query.objects.get(pk=qid)

    print(tags)

    dos = []

    for tag in range(len(tags)):
        t = Tag.objects.get(pk=tags[tag])

        user_list = []

        for user in users:
            if DocOwnership.objects.filter(query=query,user__username=user,tag=t).count() == 0:
                user_list.append(User.objects.get(username=user))


        docs = Doc.objects.filter(query=query,tag=t)
        l= len(docs)
        ssize = int(tagdocs[tag])

        my_ids = list(docs.values_list('UT', flat=True))
        rand_ids = random.sample(my_ids, ssize)
        sample = docs.filter(UT__in=rand_ids).all()
        s = 0
        for doc in sample:
            s+=1
            if docsplit=="true":
                user = user_list[s % len(user_list)]
                docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                dos.append(docown)
            else:
                for user in user_list:
                    docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                    dos.append(docown)
    DocOwnership.objects.bulk_create(dos)
    print("Done")

    return HttpResponse("<body>xyzxyz</body>")

import re

## Universal screening function, ctype = type of documents to show
def screen(request,qid,tid,ctype,d=0):
    d = int(d)
    ctype = int(ctype)
    query = Query.objects.get(pk=qid)
    tag = Tag.objects.get(pk=tid)
    user = request.user


    back = 0

    docs = DocOwnership.objects.filter(
            doc__wosarticle__isnull=False,
            query=query,
            user=user.id,
            tag=tag
    )
    if ctype==5:
        docs = docs.filter(relevant__gte=1)
    else:
        docs = docs.filter(relevant=ctype)
    if d < 0:
        d = docs.count() - 1
        back = -1

    docs = docs.order_by('date')

    tdocs = docs.count()
    sdocs = d

    ndocs = docs.count()

    try:
        doc_id = docs[d].doc_id
    except:
        return HttpResponseRedirect(reverse('scoping:userpage'))

    pages = ["check","review","review","maybe","yesbut","review"]

    doc = Doc.objects.filter(UT=doc_id).first()
    authors = DocAuthInst.objects.filter(doc=doc)
    abstract = highlight_words(doc.content,query)
    title = highlight_words(doc.wosarticle.ti,query)

    qtechs = Technology.objects.filter(query__doc=doc) | Technology.objects.filter(doc=doc)
    qtechs = qtechs.distinct()
    ntechs = Technology.objects.exclude(query__doc=doc).exclude(doc=doc)

    qinns = Innovation.objects.filter(query__doc=doc) | Innovation.objects.filter(doc=doc)
    qinns = qinns.distinct()
    ninns = Innovation.objects.exclude(query__doc=doc).exclude(doc=doc)

    if query.innovation is not None:
        innovation=True
    else:
        innovation=False

    #x = y

    template = loader.get_template('scoping/doc.html')
    context = {
        'query': query,
        'doc': doc,
        'ndocs': ndocs,
        'user': user,
        'authors': authors,
        'tdocs': tdocs,
        'sdocs': sdocs,
        'abstract': abstract,
        'title': title,
        'page': pages[ctype],
        'ctype': ctype,
        'qtechs': qtechs,
        'ntechs': ntechs,
        'innovation': innovation,
        'qinns': qinns,
        'ninns': ninns,
        'tag': tag,
        'd': d,
        'back': back
    }

    return HttpResponse(template.render(context, request))

def do_review(request):

    tid = request.GET.get('tid',None)
    qid = request.GET.get('query',None)
    doc_id = request.GET.get('doc',None)
    d = request.GET.get('d',None)

    doc = Doc.objects.get(pk=doc_id)
    query = Query.objects.get(pk=qid)
    user = request.user
    tag = Tag.objects.get(pk=tid)

    docown = DocOwnership.objects.filter(doc=doc,query=query,user=user,tag=tag).order_by("relevant").first()

    print(docown.relevant)

    print(docown.user.username)
    print(docown.doc.UT)

    docown.relevant=int(d)
    docown.date=timezone.now()
    docown.save()
    print(docown.relevant)

    time.sleep(1)
    return HttpResponse("")

def remove_assignments(request):
    qid = request.GET.get('qid',None)
    query = Query.objects.get(pk=qid)
    todelete = DocOwnership.objects.filter(query=query)
    DocOwnership.objects.filter(query=int(qid)).delete()
    return HttpResponse("")

def editdoc(request):
    doc_id = request.POST.get('doc',None)
    field = request.POST.get('field',None)
    value = request.POST.get('value',None)

    doc = Doc.objects.get(pk=doc_id)
    if field == "content":
        doc.content=value
        doc.wosarticle.ab=value
        doc.save()

    print(doc_id)
    print(field)
    print(value)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def delete(request,thing,thingid):
    from scoping import models
    getattr(models, thing).objects.get(pk=thingid).delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def remove_tech(request,doc_id,tid,thing='Technology'):
    doc = Doc.objects.get(pk=doc_id)
    obj = apps.get_model(app_label='scoping',model_name=thing).objects.get(pk=tid)
    getattr(doc,thing.lower()).remove(obj)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def add_note(request):
    doc_id = request.POST.get('docn',None)
    tid = request.POST.get('tag',None)
    qid = request.POST.get('qid',None)
    ctype = request.POST.get('ctype',None)
    d = request.POST.get('d',None)
    text = request.POST.get('note',None)

    doc = Doc.objects.get(pk=doc_id)
    note = Note(
        doc=doc,
        user=request.user,
        date=timezone.now(),
        text=text
    )
    note.save()


    return HttpResponseRedirect(reverse('scoping:screen', kwargs={
        'qid': qid,
        'tid': tid,
        'ctype': ctype,
        'd': d
    }))




#########################################################
## Download the queryset


def download(request, qid):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="documents.csv"'

    writer = csv.writer(response)

    headers = []

    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name
        if f.name !="doc":
            headers.append({"path": path, "name": f.verbose_name})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query":
            headers.append({"path": path, "name": f.verbose_name})

    hrow = [x['name'] for x in headers]
    fields = [x['path'] for x in headers]

    writer.writerow(hrow)

    q = Query.objects.get(pk=qid)
    docs = Doc.objects.filter(query=q)
    docvals = docs.values(*fields)
    for d in docvals:
        row = [d[x] for x in fields]
        writer.writerow(row)


    return response

def doc_tech(request):
    did = request.GET.get('did',None)
    tid = request.GET.get('tid',None)
    doc = Doc.objects.get(pk=did)
    tech = Technology.objects.get(pk=tid)
    doc.technology.add(tech)
    doc.save()
    return HttpResponse()

def doc_inn(request):
    did = request.GET.get('did',None)
    iid = request.GET.get('tid',None)
    doc = Doc.objects.get(pk=did)
    inn = Innovation.objects.get(pk=iid)
    doc.innovation.add(inn)
    doc.save()
    return HttpResponse()

from django.contrib.auth import logout
def logout_view(request):
    logout(request)
    # Redirect to a success page.
    #return HttpResponse("logout")
    return HttpResponseRedirect(reverse('scoping:index'))

def add_manually():

    qid = 308
    tag = 61
    user = User.objects.get(username="delm")
    query = Query.objects.get(id=qid)
    t = Tag.objects.get(pk=tag)
    docs = Doc.objects.filter(query=query,tag=t).distinct()
    for doc in docs:
        try:
            DocOwnership.objects.get(doc=doc,query=query,user=user,tag=tag)
        except:
            docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
            docown.save()
            print("new docown added")

    return HttpResponse("")

import string
def highlight_words(s,query):
    if query.database == "intern":
        args = query.text.split(" ")
        q1 = Query.objects.get(id=args[0])
        q2 = Query.objects.get(id=args[2])
        qwords = [re.findall('\w+',query.text) for query in [q1,q2]]
        qwords = [item for sublist in qwords for item in sublist]
    else:
        qwords = re.findall('\w+',query.text)
    nots = ["TS","AND","NOT","NEAR","OR","and","W"]
    transtable = {ord(c): None for c in string.punctuation + string.digits}
    qwords = set([x.split('*')[0].translate(transtable) for x in qwords if x not in nots and len(x.translate(transtable)) > 0])
    print(qwords)
    abstract = []
    for word in s.split(" "):
        h = False
        for q in qwords:
            if q in word:
                h = True
        if h:
            abstract.append('<span class="t1">'+word+'</span>')
        else:
            abstract.append(word)
    return(" ".join(abstract))
