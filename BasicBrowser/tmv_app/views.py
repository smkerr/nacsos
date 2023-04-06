from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Template, Context, RequestContext, loader
from tmv_app.models import *
from scoping.models import *
import parliament.models as pm
from django.db.models import Q, F, Sum, Count, FloatField, Case, When, Value, Max
from django.shortcuts import *
from django.forms import ModelForm
import random, sys, datetime
import urllib.request
from nltk.stem import SnowballStemmer
from django.http import JsonResponse
import json, csv
import decimal
from django.core import management
from .tasks import *
from celery import group
from utils.tm_mgmt import *
import pandas as pd
from sklearn.preprocessing import normalize
from .forms import *

# the following line will need to be updated to launch the browser on a web server
TEMPLATE_DIR = sys.path[0] + '/templates/'

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

global run_id

def get_year_filter(request):
    try:
        y1 = request.session['y1']
        y2 = request.session['y2']
    except:
        y1 = 1990
        y2 = 2016
        request.session['y1'] = y1
        request.session['y2'] = y2

    return([y1,y2])

def show_toolbar(request):
    return True
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK" : show_toolbar,
}

def author_detail(request, author_name, run_id):
    response = author_name

    stat = RunStats.objects.get(pk=run_id)

    documents = Doc.objects.filter(docauthinst__AU=author_name).distinct()

    dt_threshold = stat.dt_threshold

    topics = DocTopic.objects.filter(
        doc__docauthinst__AU=author_name,
        scaled_score__gt=dt_threshold/80,
        run_id=run_id
    )

    topics = topics.annotate(total=(Sum('scaled_score')))

    topics = topics.values('topic','topic__title').annotate(
        tprop=Sum('scaled_score')
    ).order_by('-tprop')

    pie_array = []
    for t in topics:
        pie_array.append([t['tprop'], '/topic/' + str(t['topic']), 'topic_' + str(t['topic'])])

    author_template = loader.get_template('tmv_app/author.html')

    author_page_context = {
        'author': author_name,
        'docs': documents,
        'topics': topics,
        'pie_array': pie_array,
        'run_id': run_id
    }

    return HttpResponse(author_template.render(author_page_context))

###########################################################################
## Institution view
def institution_detail(request, run_id, institution_name):
    documents = Doc.objects.filter(
        docauthinst__institution__icontains=institution_name
    ).distinct('UT')

    topics = {}
    topics = Topic.objects.all()
    topics = []

    topics = DocTopic.objects.filter(
        doc__docauthinst__institution__icontains=institution_name,
        scaled_score__gt=0.00002,run_id=run_id
    )

    topics = topics.annotate(total=(Sum('scaled_score')))

    topics = topics.values('topic','topic__title').annotate(
        tprop=Sum('scaled_score')
    ).order_by('-tprop')

    pie_array = []
    for t in topics:
        pie_array.append([t['tprop'], '/topic/' + str(t['topic']), 'topic_' + str(t['topic'])])

    institution_template = loader.get_template('tmv_app/institution.html')

    institution_page_context = {
        'institution': institution_name,
        'docs': documents,
        'topics': topics,
        'pie_array': pie_array
    }

    return HttpResponse(institution_template.render(institution_page_context))

def network(request,run_id, csvtype=None):

    # check if network has already been calculated
    if not (DynamicTopicCorr.objects.filter(run_id=run_id)
            or TopicCorr.objects.filter(run_id=run_id)):
        management.call_command('corr_topics', run_id)

    ar = -1
    stat = RunStats.objects.get(pk=run_id)
    if stat.method=="DT":
        topics = DynamicTopic
        topiccorrs = DynamicTopicCorr
    else:
        topics = Topic
        topiccorrs = TopicCorr
    template = loader.get_template('tmv_app/network.html')
    nodes = topics.objects.filter(run_id=run_id)
    nodes = nodes.annotate(
                arscore = F('score')
            )

    nodes = nodes.values('id','title','arscore','score')
    links = topiccorrs.objects.filter(run_id=run_id).filter(score__gt=0.05,score__lt=1,ar=ar).annotate(
        source=F('topic'),
        target=F('topiccorr')
    )

    if csvtype:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{csvtype}_{run_id}.csv"'

        writer = csv.writer(response,delimiter=',')
        writer.writerow(['sep=,'])

        if csvtype=="nodes":
            fields = ('id','score','title')
            writer.writerow(fields)
            for n in nodes:
                writer.writerow([n[f] for f in fields])
        elif csvtype=="links":
            fields = ("source", "target", "score")
            writer.writerow(fields)
            for l in links.values(*fields):
                writer.writerow([l[f] for f in fields])

        return response

    nodes = json.dumps(list(nodes),indent=4,sort_keys=True)
    links = json.dumps(list(links.values('source','target','score')),indent=4,sort_keys=True)

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    context = {
        "nodes":nodes,
        "links":links,
        "run_id":run_id,
        "stat": RunStats.objects.get(pk=run_id),
        "project": project
    }

    return HttpResponse(template.render(context, request))

def return_corrs(request):
    cor = float(request.GET.get('cor',None))
    run_id = int(request.GET.get('run_id',None))
    ar = int(request.GET.get('ar',-1))
    stat = RunStats.objects.get(pk=run_id)
    if stat.method=="DT":
        topics = DynamicTopic
        topiccorrs = DynamicTopicCorr
        tars = DynamicTopicARScores
        field = 'dynamictopicarscores__score'
    else:
        topics = Topic
        topiccorrs = TopicCorr
        tars = TopicARScores
        field = 'topicarscores__score'
    nodes = topics.objects.filter(run_id=run_id)
    if ar > -1:
        a = AR.objects.get(ar=ar)
        nodes = topics.objects.filter(run_id=run_id)

        if stat.method=="DT":
            nodes = nodes.annotate(
                arscore = Sum(
                    Case(When(
                        dynamictopicarscores__ar=a,
                        then=F(field)),
                        output_field=models.FloatField()
                    )
                )
            )
        else:
            nodes = nodes.annotate(
                arscore = Sum(
                    Case(When(
                        topicarscores__ar=a,
                        then=F(field)),
                        output_field=models.FloatField()
                    )
                )
            )
    else:
        nodes = nodes.annotate(
            arscore = F('score')
        )
    nodes = list(nodes.values('id','title','score','arscore'))
    links = topiccorrs.objects.filter(run_id=run_id).filter(
        score__gt=cor,
        score__lt=1,
        ar=ar
    ).annotate(
        source=F('topic'),
        target=F('topiccorr')
    )
    links = list(links.values('source','target','score'))
    context = {
        "nodes":nodes,
        "links":links
    }
    return HttpResponse(json.dumps(context,sort_keys=True))


def growth_heatmap(request, run_id):
    template = loader.get_template('tmv_app/growth_heatmap.html')
    stat = RunStats.objects.get(pk=run_id)
    context = {
        'run_id': run_id,
        'stat': stat
    }
    return HttpResponse(template.render(context, request))

def growth_json(request, run_id, v='pgrowthn'):

    stat = RunStats.objects.get(pk=run_id)

    if stat.method == "DT":

        ars = TimeDTopic.objects.filter(
            dtopic__run_id=run_id#,
            #ar__ar__isnull=False,
            #ar__ar__gt=0
        )

        df = pd.DataFrame.from_dict(
            list(ars.values(
                'dtopic__title',
                'period__title',
                v,
                'dtopic__ipcc_coverage'
            ))
        )
        ppdf = df.pivot('dtopic__title','period__title',v).fillna(0)

        col_ids = DynamicTopic.objects.filter(
            run_id=run_id,
            timedtopic__isnull=False
        ).order_by('title').values_list('id',flat=True)


    else:

        ars = TopicARScores.objects.filter(
            topic__run_id=run_id,
            ar__ar__isnull=False,
            ar__ar__gt=0
        )

        df = pd.DataFrame.from_dict(
            list(ars.values('topic__title','ar__name', v, 'topic__ipcc_coverage'))
            )
        ppdf = df.pivot('topic__title','ar__name', v).fillna(0)

        #ndf =
        col_ids = Topic.objects.filter(
            run_id=run_id,
            topicarscores__isnull=False
        ).order_by('title').values_list(
            'id',flat=True
        )

    json = ppdf.to_json(orient="split")

    return JsonResponse([json,list(col_ids)], safe=False)

def compare_runs(request, a, z):

    fname = management.call_command('compare_topics',a, z)

    with open(fname,"rb") as f:

        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="'+fname+'"'

    return response

def topics_time(request, run_id, stype):
    stat = RunStats.objects.get(pk=run_id)
    if stat.method=="DT":
        topics = DynamicTopic.objects.filter(run_id=run_id)
        yts = DynamicTopicYear.objects.filter(run_id=run_id)#, PY__lt=2016)
        #yts = DynamicTopicYear.objects.filter(run_id=run_id, PY__in=[2010,2011,2012])
    else:
        topics = Topic.objects.filter(run_id=run_id)

    template = loader.get_template('tmv_app/topics_time.html')

    yts = yts.order_by(
        'topic__score','PY'
    ).values(
        'topic__id',
        'topic__title',
        'PY',
        'score',
        'share'
    )

    if int(stype)==0:
        stype='score'
    else:
        stype='share'

    context = {
        'yts': list(yts),
        'stype': stype

    }

    return HttpResponse(template.render(request =request, context=context))


#######################################################################

def dynamic_topic_detail(request,topic_id):
    """ Dynamic Topic view (for dynamic NMF) """

    template = loader.get_template('tmv_app/dynamic_topic.html')

    topic = DynamicTopic.objects.get(pk=topic_id)
    run_id = topic.run_id.run_id

    stat = RunStats.objects.get(pk=run_id)

    if stat.parent_run_id is not None:
        run_id=stat.parent_run_id

    topicterms = Term.objects.filter(
        dynamictopicterm__topic=topic,
        run_id=run_id,
        dynamictopicterm__score__gt=0.00001,
        dynamictopicterm__PY__isnull=True
    ).order_by('-dynamictopicterm__score')[:50]

    ytterms = []

    tts = DynamicTopicTerm.objects.filter(
        topic=topic,
        PY__isnull=False
    )

    m = tts.aggregate(models.Max('score'))['score__max']
    if m is None:
        m = 0
    min = stat.dyn_win_threshold

    for py in tts.distinct('PY') \
        .order_by('PY').values_list('PY',flat=True):
        ytts = tts.filter(
            PY=py,
            score__gt=stat.dyn_win_threshold
        ).order_by('-score')[:10]

        for t in ytts:
            #t.scaled_score=t.score/m
            t.scaled_score=np.log(1+t.score)/np.log(1+m)


        if ytts.count() > 0:
            ytterms.append(ytts)

    #x = y

    yscores = list(TimeDTopic.objects.filter(
        dtopic=topic
    ).order_by('period__n').values('period__n','score'))


    wtopics = Topic.objects.filter(
        #run_id=run_id,
        topicdtopic__dynamictopic__run_id=run_id,
        primary_dtopic=topic
    ).distinct().order_by('year')

    for t in wtopics:
        t.tts = Term.objects.filter(
            topicterm__topic=t,
            #run_id=run_id,
            topicterm__score__gt=0.00001
        ).order_by('-topicterm__score')[:10].annotate(
            score=F('topicterm__score')
        )

        score = TopicDTopic.objects.get(
            topic=t,dynamictopic=topic
        ).score

        for term in t.tts:
            tot_score = term.score*score
            term.scaled_score = np.log(1+tot_score)/np.log(1+m)
        t.score = round(score,2)

    docs = DocTopic.objects.filter(
            #topic__primary_dtopic=topic,
            #run_id=run_id,
            topic__topicdtopic__dynamictopic=topic,
            topic__topicdtopic__score__gt=0.05,
            score__gt=0.05#,
            #doc__ipccref__isnull=False
        )

    if stat.query:

        docs = docs.annotate(
            topic_combination = F('score') * F('topic__topicdtopic__score')
        ).order_by('-topic_combination')[:50].values(
            'doc__pk','doc__PY','doc__title','topic_combination'
        )
    elif stat.psearch:
        if stat.psearch.search_object_type == 1: # paragraph
            docs = docs.annotate(
                topic_combination = F('score') * F('topic__topicdtopic__score')
            ).order_by('-topic_combination')[:50].values(
                'par__utterance__pk','par__utterance__document__parlperiod__n','par__utterance__speaker','topic_combination'
            )
        elif stat.psearch.search_object_type == 2: # utterance
            docs = docs.annotate(
                topic_combination = F('score') * F('topic__topicdtopic__score')
            ).order_by('-topic_combination')[:50].values(
                'ut__pk','ut__document__parlperiod__n','ut__speaker','topic_combination'
            )
    else:
        docs = None

    dtopics = Topic.objects.filter(
        run_id=run_id,
        year__lt=2200
    ).order_by('year').annotate(
        dscore = Sum(
            Case(
                When(topicdtopic__dynamictopic=topic,
                    then=F('topicdtopic__score')),
                default=0,
                output_field=models.FloatField()
            )
        )
    )

    ysums = Topic.objects.filter(
        run_id=run_id,
        year__lt=2200
    ).order_by('year').values('year').annotate(
        sum = Sum('score'),
    )

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    context = {
        'project': project,
        'stat': stat,
        'run_id': run_id,
        'topic': topic,
        'topicterms': topicterms,
        'wtopics': wtopics,
        'wtvs': list(dtopics.values('title','score','year','dscore','id')),
        'ysums': list(ysums.values('year','sum')),
        'docs': docs,
        'ytterms': ytterms,
        'yscores': yscores,
        'user': request.user
    }
    return HttpResponse(template.render(request =request, context=context))


# Topic page for Blei dynamic topics
def dtopic_detail(request,topic_id):
    """
    View for dynamic topics from Blei dtm

    :param request:
    :param topic_id:
    :return:
    """

    template = loader.get_template('tmv_app/dtopic.html')

    topic = Topic.objects.get(pk=topic_id)
    stat = topic.run_id

    tterms = []
    tts = TopicTerm.objects.filter(topic=topic)
    tdts = TopicTimePeriodScores.objects.filter(
        topic=topic
    ).order_by('period__n')
    for i, p in enumerate(stat.periods.all().order_by('n')):
        ytts = tts.filter(
            PY=p.n#+1
        ).order_by('-score')[:10].select_related('term')
        #tdt = tdts[i]
        try:
            tdt = tdts.get(period=p)
            tdt.share = tdt.share*100
        except:
            print("failed to retrieve share")
            tdt = None
        tterms.append({
            "ytts": ytts,
            "tdt": tdt,
            "period": p
        })
        #x = y

    docs = Doc.objects.filter(doctopic__topic=topic) \
        .order_by('-doctopic__score')[:50]

    run_id = topic.run_id.pk
    stat = RunStats.objects.get(run_id=run_id)

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    ytarray = None

    yts = TopicTimePeriodScores.objects.filter(
        topic__run_id=topic.run_id
    ).order_by('period__n')
    ytarray = list(yts.values(
        'period__n','share','score','topic_id','topic__title'
    ))

    ytarray0 = [y for y in ytarray if y['topic_id'] != topic.id]
    ytarray = ytarray0 + [y for y in ytarray if y['topic_id'] == topic.id]

    context = {
        "project": project,
        "run_id": run_id,
        "topic":topic,
        "tterms": tterms,
        "docs": docs,
        "user": request.user,
        "yts": ytarray
    }

    return HttpResponse(template.render(context))

###########################################################################
def get_topicterms(request, topic_id):
    topic = Topic.objects.get(pk=topic_id)
    l = request.GET.get('l', 1)
    template = loader.get_template('tmv_app/snippets/topicterms.html')

    topicterms = topic.relevant_words(float(l), 25).values(
        'term__title','score','term__id','alltopic_score'
    )
    max_term_score = max([x['alltopic_score'] for x in topicterms])

    context = {
        "run_id": topic.run_id.pk,
        "topicterms": topicterms,
        "max_term_score": max_term_score,
        "l": l
    }

    return HttpResponse(template.render(context, request))

def topic_detail(request, topic_id, run_id=0):
    """
    Topic view

    :param request:
    :param topic_id:
    :param run_id:
    :return:
    """

    template = loader.get_template('tmv_app/topic.html')
    topic = Topic.objects.get(pk=int(topic_id))
    try:
        topic = Topic.objects.get(pk=int(topic_id))
    except:
        pass
        #return(topic_detail_hlda(request, topic_id))

    if topic.run_id.method=="BD":
        return(dtopic_detail(request,topic_id))
    if run_id==0:
        run_id = topic.run_id.pk
    stat = RunStats.objects.get(run_id=run_id)


    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    topic_template = loader.get_template('tmv_app/topic.html')

    if request.method=="POST":
        t = request.POST.get('title',None)
        if t is not None:
            if topic.original_title is None:
                topic.original_title = topic.title
            topic.title=t
            topic.manual_title=t
            topic.save()

    if stat.query:
        ndocs = Doc.objects.filter(
            doctopic__topic=topic,
            doctopic__run_id=run_id,
            doctopic__score__gt=stat.dt_threshold
        ).count()

        ### Journals
        journals = JournalAbbrev.objects.filter(
            doc__doctopic__topic=topic,
            doc__doctopic__run_id=stat.run_id,
            doc__journal__isnull=False,
            doc__doctopic__score__gt=stat.dt_threshold
        ).values('fulltext').annotate(
            score=Sum('doc__doctopic__score'),
            no_docs=Count('doc__doctopic__score')
        ).order_by('-score')[:10]

    elif stat.psearch.search_object_type == 1:
        ndocs = pm.Paragraph.objects.filter(
            doctopic__topic=topic,
            doctopic__run_id=run_id,
            doctopic__score__gt=stat.dt_threshold
        ).count()
        journals = None
    else:
        ndocs = pm.Utterance.objects.filter(
            doctopic__topic=topic,
            doctopic__run_id=run_id,
            doctopic__score__gt=stat.dt_threshold
        ).count()
        journals = None

    stat = RunStats.objects.get(pk=run_id)
    if stat.method not in ["DT","BD"]:
        yts = TopicYear.objects.filter(run_id=run_id)
        ytarray = list(yts.values('PY','count','score','topic_id','topic__title'))
    else:
        yts = None
        ytarray= None

    corrtops = TopicCorr.objects.filter(
        topic=topic_id,score__lt=1,ar=-1
    ).order_by('-score')[:10]
    if stat.method =="DT":
        dtops = TopicDTopic.objects.filter(
            topic=topic_id,
            dynamictopic__run_id=run_id
        ).order_by('-score')[:10]
    else:
        dtops = None


    topic_page_context = {
        'topic': topic,
        'yts': ytarray,
        'corrtops': corrtops,
        'dtops': dtops,
        'run_id': run_id,
        'stat': stat,
        'journals': journals,
        'ndocs': ndocs,
        'project': project,
        'user': request.user
    }

    return HttpResponse(topic_template.render(topic_page_context, request))

def get_yt_csv(request, run_id):
    stat = RunStats.objects.get(pk=run_id)
    if stat.method not in ["DT","BD"]:
        yts = TopicYear.objects.filter(run_id=run_id)

        fields = ('PY','share','score','topic_id','topic__title')
        ytarray = yts.values(*fields)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="topic_years.csv"'

        writer = csv.writer(response,delimiter=',')
        writer.writerow(['sep=,'])

        writer.writerow(fields)

        for yt in ytarray:
            writer.writerow(yt.values())

        return response

def get_topic_docs(request,topic_id):

    template = loader.get_template('tmv_app/topic_docs.html')
    topic = Topic.objects.get(pk=topic_id)
    run_id = topic.run_id.pk

    stat = RunStats.objects.get(run_id=run_id)

    dt_threshold = stat.dt_threshold
    dt_thresh_scaled = stat.doc_topic_scaled_score
    if stat.method=="BD":
        dt_threshold=dt_threshold*100

    svalue = request.GET.get('sort',None)
    sortcol = svalue.replace('-','')

    if stat.query:

        doctopics = Doc.objects.filter(
            doctopic__run_id=run_id,
            doctopic__topic=topic,
            doctopic__score__gt=dt_threshold
        )

        if sortcol != "doctopic__score":
            doctopics = doctopics.filter(**{sortcol+'__isnull': False})
        doctopics = doctopics.order_by(svalue)[:50]


        doctopics = doctopics.annotate(
            svalue=F(sortcol)
        )
        doctopics = doctopics.values('PY','title','pk','doctopic__score','svalue')

        d = decimal.Decimal(doctopics[0]['svalue'])
        float = abs(d.as_tuple().exponent)
        if float > 3:
            float=4

    elif stat.psearch:

        if stat.psearch.search_object_type == 1:
            doctopics = pm.Paragraph.objects.filter(
                doctopic__topic=topic,doctopic__run_id=run_id,
                doctopic__score__gt=dt_threshold
            )
        else:
            doctopics = pm.Utterance.objects.filter(
                doctopic__topic=topic,doctopic__run_id=run_id,
                doctopic__score__gt=dt_threshold
            )

        if sortcol != "doctopic__score":
            doctopics = doctopics.filter(**{sortcol+'__isnull': False})
        doctopics = doctopics.order_by(svalue)[:50]

        doctopics = doctopics.annotate(
            svalue=F(sortcol)
        )

        if stat.psearch.search_object_type == 1:
            doctopics = doctopics.values('pk','doctopic__score','svalue',
                                         'utterance__speaker__clean_name', 'utterance__speaker__pk')
        else:
            doctopics = doctopics.values('pk', 'doctopic__score', 'svalue',
                                         'speaker__clean_name', 'speaker__pk')

        d = decimal.Decimal(doctopics[0]['svalue'])
        float = abs(d.as_tuple().exponent)
        if float > 3:
            float=4

    context = {
        "docs": doctopics,
        "stat": stat,
        "svalue": sortcol,
        "topic": topic,
        "float": float
    }

    return HttpResponse(template.render(context))


def multi_topic(request):

    template = loader.get_template('tmv_app/multi_topic_docs.html')
    topics = request.GET.getlist('topics[]',None)

    doctopics = DocTopic.objects.filter(
        topic__in=topics,
        score__gt=0
    )
    x = doctopics.values()[:5]

    combine = doctopics.values('doc').annotate(
        topic_combination = Sum('score'),
        count = Count('score')
    ).filter(count__gte=len(topics))

    annotation = {}

    combine2 = combine.values('doc')
    for t in topics:
        annotation[t] = Sum(
            Case(When(topic=t,then=F('score')),
                #default=0,
                output_field=models.FloatField()
            )
        )

    combine2 = combine2.annotate(**annotation)
    combine2 = combine2.annotate(topic_combination=F(topics[0]))

    for i in range(1,len(topics)):
        combine2 = combine2.annotate(
            topic_combination=F('topic_combination')*F(topics[i])
        )

    y = combine2.order_by('-topic_combination')[:50]
    y= y.values('doc__pk','doc__PY','doc__title','topic_combination')

    context = {
        'docs' : y,
        'topic': Topic.objects.get(pk=topics[0])
    }

    return HttpResponse(template.render(context))


##############################################################

def term_detail(request, run_id, term_id):
    """
    View for details of a topic term

    :param request:
    :param run_id:
    :param term_id:
    :return:
    """

    allnodes = []
    alllinks = []
    terms = []

    term_template = loader.get_template('tmv_app/term.html')

    for term_id in [term_id]:#,264]:
        term = Term.objects.get(pk=term_id,run_id=run_id)
        terms.append(term)
        topics = TopicTerm.objects.filter(term=term_id,run_id=run_id).order_by('-score')
        if len(topics) > 0:
            topic_tuples = []
            max_score = topics[0].score
            for topic in topics:
                topic_tuples.append((topic.topic, topic.score, topic.score/max_score*100))

        topicobjs = Topic.objects.filter(
            topicterm__term=term,run_id=run_id
        ).order_by('-topicterm__score').annotate(
            type=Value('topic', output_field=models.CharField())
        )

        new_term_id = 'term_'+str(term_id)

        new_term_id = term_id

        nodes = list(topicobjs.values('id', 'title', 'score', 'type'))

        nodes.append({
            'id': new_term_id,
            'title': term.title,
            'score': 1000,
            'type': 'word'
        })

        #nodes = json.dumps(nodes, indent=4, sort_keys=True)

        links = topics.annotate(
            source=Value(new_term_id, output_field=models.CharField()),
            target=F('topic__id'),
            type=Value(0, output_field=models.IntegerField())
        )

        tlinks = TopicCorr.objects.filter(
            run_id=run_id,
            topic__in=topicobjs,
            topiccorr__in=topicobjs,
            score__gt=0.05,
            score__lt=1
        ).annotate(
            type=Value(1, output_field=models.IntegerField()),
            source=F('topic'),
            target=F('topiccorr')#,
            #tscore=F('score')
        )

        tlinks = list(tlinks.values('source','target','score'))

        for l in tlinks:
            l['score'] = l['score']/100000000

        #x = y

        links = list(links.values('source','target','score'))

        allnodes = allnodes + nodes
        alllinks = alllinks + links + tlinks

    allnodes = json.dumps(allnodes,indent=4,sort_keys=True)
    alllinks = json.dumps(alllinks,indent=4,sort_keys=True)

    term_page_context = {
        'term': term,
        'terms': terms,
        'topic_tuples': topic_tuples,
        'run_id': run_id,
        'nodes': allnodes,
        'links': alllinks
    }

    return HttpResponse(term_template.render(term_page_context))


def network_wg(request, run_id, t=5, f=100,top=0):
    """
    View of topic network

    :param request:
    :param run_id:
    :param t:
    :param f:
    :param top:
    :return:
    """
    ar = -1
    force = int(f) * -1
    t = int(t) / 100
    top = int(top)

    template = loader.get_template('tmv_app/network_wg.html')

    stat = RunStats.objects.get(pk=run_id)
    if stat.method =="DT":
        nodes = DynamicTopic.objects.filter(run_id=run_id)
        tc = DynamicTopicCorr
        topic_type = DynamicTopic
    else:
        nodes = Topic.objects.filter(run_id=run_id)
        tc = TopicCorr
        topic_type = Topic

    for n in nodes.filter(primary_wg__isnull=True):
        wgs = list(IPCCRef.objects.filter(
            doc__doctopic__topic=n
        ).values('wg__wg').annotate(
            tscore = models.Sum('doc__doctopic__score')
        ))
        try:
            pwg = max(wgs, key=lambda x:x['tscore'])
            n.primary_wg =  pwg['wg__wg']
            total = sum(wg['tscore'] for wg in wgs)
            n.wg_prop = pwg['tscore'] / total
        except:
            n.primary_wg = None
        n.save()

    nodes = list(nodes.order_by('-score').values(
        'id','title','score','primary_wg','wg_prop'
    ))

    if int(top) != 0:
        if top < 0:
            topic = topic_type.objects.filter(
                run_id=run_id,
                primary_wg=abs(top)
            )

            if stat.method=="DT":
                topic = topic.annotate(
                    links = models.Sum(
                        models.Case(
                            models.When(
                                dynamictopiccorr__score__gt=t,
                                dynamictopiccorr__ar=ar,
                                then=1
                            ),
                            default=0,
                            output_field=models.IntegerField()
                        )
                    )
                ).order_by('-score').first()
            else:
                topic = topic.annotate(
                links = models.Sum(
                    models.Case(
                        models.When(
                            topiccorr__score__gt=t,topiccorr__ar=ar,then=1
                        ),
                        default=0,
                        output_field=models.IntegerField()
                    )
                )
            ).order_by('-score').first()
        else:
            topic = topic_type.objects.get(pk=int(top))

        if stat.method!="DT":
            corrs = list(topic_type.objects.filter(
                topiccorr__topiccorr=topic,
                topiccorr__score__gt=t,
                topiccorr__ar=ar
            ).values_list('id',flat=True))
        else:
            corrs = list(topic_type.objects.filter(
                dynamictopiccorr__topiccorr=topic,
                dynamictopiccorr__score__gt=t,
                dynamictopiccorr__ar=ar
            ).values_list('id',flat=True))
        top_id = topic.id
    else:
        top_id = 0
    i = 0
    for wg in [1,2,3]:
        i = 0
        for n in nodes:
            if n['primary_wg'] == wg:
                i+=1
                n['wgrank'] = i
    for n in nodes:
        i+=1
        n['rank'] = i
        if int(top) != 0:
            if n['id'] in corrs:
                n['wgrank'] = 1
            else:
                n['wgrank'] = 50

    links = tc.objects.filter(run_id=run_id).filter(
        score__gt=t,
        score__lt=1,
        ar=ar
    ).annotate(
        source=F('topic'),
        target=F('topiccorr')
    )


    nodes = json.dumps(nodes,indent=4,sort_keys=True)

    links = json.dumps(list(links.values('source','target','score')),indent=4,sort_keys=True)


    context = {
        "nodes":nodes,
        "links":links,
        "run_id":run_id,
        "stat": RunStats.objects.get(pk=run_id),
        "force": force,
        "top_id": top_id
    }


    return HttpResponse(template.render(context))

#######################################################################

def doc_detail(request, doc_id, run_id):
    """
    View of document details

    :param request:
    :param doc_id:
    :param run_id:
    :return:
    """

    snowball_stemmer = SnowballStemmer("english")

    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(doc_detail_hlda(request, doc_id))
    #update_topic_titles(int(run_id))
    response = ''
    template = loader.get_template('tmv_app/doc.html')

    doc = Doc.objects.get(id=doc_id)

    if stat.parent_run_id:
        parent_run_id=stat.parent_run_id
    else:
        parent_run_id=run_id

    doctopics = DocTopic.objects.filter(doc=doc_id,run_id=parent_run_id).order_by('-score')

    doc_authors = DocAuthInst.objects.filter(doc=doc).distinct('AU')

    #doc_institutions = DocInstitutions.objects.filter(doc__UT=doc_id)
    #for di in doc_institutions:
    #    di.institution = di.institution.split(',')[0]


    ipccrefs = doc.ipccref_set.all().values('wg__ar','wg__wg')



    topics = []
    pie_array = []
    dt_threshold = stat.dt_threshold
    dt_thresh_scaled = stat.dt_threshold_scaled
    if stat.dt_threshold is not None:
        dt_threshold = stat.dt_threshold
        #dt_thresh_scaled = stat.dt_threshold


    if stat.method=="BD":
        dt_threshold=dt_threshold*100
    topicwords = {}
    ntopic = 0

    # if dt_thresh_scaled:
    #     doctopics = doctopics.filter(scaled_score__gte=dt_threshold/80)
    # else:
    #     doctopics = doctopics.filter(score__gte=dt_threshold)
    doctopics = doctopics.filter(score__gte=dt_threshold)
    for dt in doctopics:
        topic = Topic.objects.get(pk=dt.topic_id)
        ntopic+=1
        topic.ntopic = "t"+str(ntopic)
        topics.append(topic)
        if stat.method=="BD":
            terms=Term.objects.filter(
                topicterm__topic=topic.pk,
                topicterm__PY=doc.PY
            ).order_by('-topicterm__score')[:10]
        else:
            terms = Term.objects.filter(topicterm__topic=topic.pk).order_by('-topicterm__score')[:10]

        topicwords[ntopic] = []
        for tt in terms:
            topicwords[ntopic].append(tt.title)
        if not dt_thresh_scaled:
            pie_array.append([dt.score, '/nacsos-legacy/tmv_app/topic/' + str(topic.pk), 'topic_' + str(topic.pk)])
        else:
            pie_array.append([dt.scaled_score, '/nacsos-legacy/tmv_app/topic/' + str(topic.pk), 'topic_' + str(topic.pk)])


    words = []
    if stat.fulltext:
        word_hoard = doc.fulltext.split()
    else:
        word_hoard = doc.content.split()
    for word in word_hoard:
        wt = ""
        for t in reversed(range(1,ntopic+1)):
            if snowball_stemmer.stem(word) in topicwords[t] or word in topicwords[t]:
            #if word in topicwords[t]:
                wt = t
        words.append({'title': word, 'topic':"t"+str(wt)})

    if doc.wosarticle.de is not None:
        de = doc.wosarticle.de
    else:
        de = None
    if doc.wosarticle.kwp is not None:
        kwp = doc.wosarticle.kwp
    else:
        kwp = None

    context = {
        'doc': doc,
        'topics': topics,
        'pie_array': pie_array,
        'doc_authors': doc_authors,
        'words': words,
        'run_id': run_id,
        'stat': stat,
        'dt_threshold': dt_threshold,
        'ipccrefs': ipccrefs,
        'de': de,
        'kwp': kwp,
        'project': stat.query.project

    }


    return HttpResponse(template.render(request=request, context=context))

def adjust_threshold(request,run_id,what):
    value = float(request.GET.get('value',None))
    stat = RunStats.objects.get(run_id=run_id)
    setattr(stat,what,value)
    stat.save()
    response = 0
    return HttpResponse(response)

def print_table(request,run_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="topic_table.csv"'

    topics = Topic.objects.filter(run_id=run_id).order_by('-score')
    tsum = topics.aggregate(
        tsum=Sum('score')
    )

    for t in topics:
        termlist= list(Term.objects.filter(
            topicterm__topic=t, run_id=run_id,
            topicterm__score__gt=0.00001
        ).order_by('-topicterm__score')[:10].values_list('title',flat=True))
        t.terms = "; ".join(termlist)
        t.mtd = t.score/tsum['tsum']*100

    writer = csv.writer(response,delimiter=',')
    writer.writerow(['sep=,'])

    writer.writerow(["Topic ID","Topic Name","Stemmed Keywords","Marginal Topic Distribution"])

    for t in topics:
        row = [t.pk,"",t.terms,t.mtd]
        writer.writerow(row)

    return response

#################################################################


def topic_presence_detail(request,run_id):
    """
    Main page of topic models

    :param request:
    :param run_id:
    :return:
    """

    stat = RunStats.objects.get(run_id=run_id)
    template = loader.get_template('tmv_app/topic_presence.html')
    if stat.get_method_display() == 'hlda':
        return(topic_presence_hlda(request))

    if stat.method == "DT":
        #update_dtopics(run_id)
        return dtm_home(request,run_id)
    if stat.method == "BD":
        pass
        #update_bdtopics(run_id)

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    context = {
        'run_id': run_id,
        'stat': stat,
        'project': project,
        'user': request.user
    }

    if stat.status==3:
        run_id = int(run_id)

        response = ''

        get_year_filter(request)


        if stat.method=="DT":
            topics = DynamicTopic.objects.filter(run_id=run_id).order_by('-score')
        else:
            topics = Topic.objects.filter(run_id=run_id).order_by('-score')
        max_score = topics[0].score

        topic_tuples = []
        for topic in topics:
            s = topic.score
            topic_tuples.append((topic, topic.score, topic.score/max_score*100))

        context['topic_tuples'] = topic_tuples
    else:
        context['unfinished'] = True

    return HttpResponse(template.render(context))


def dtm_home(request, run_id):
    """
    Main page of dynamic topic model (dynamic NMF)

    :param request:
    :param run_id:
    :return:
    """
    template = loader.get_template('tmv_app/dtm_home.html')

    stat=RunStats.objects.get(pk=run_id)

    wtopics = Topic.objects.filter(
        run_id=stat.parent_run_id
    ).order_by('period','-score')

    dtopics = DynamicTopic.objects.filter(
        run_id=run_id
    ).order_by('-score')

    periods = stat.periods.order_by('n')
    for p in periods:
        p.w = 100/periods.count()
        p.ds = TimeDocTotal.objects.get(run=stat,period=p)
        p.ts = wtopics.filter(period=p)
        # for wt in p.ts:
        #     try:
        #         wt.pt = wt.primary_dtopic.get(run_id=stat.run_id).id
        #     except:
        #         wt.pt = None

    dtopics.n_docs = stat.docs_seen

    yscores = list(TimeDTopic.objects.filter(
        dtopic__run_id=run_id,
        share__isnull=False
    ).values('period__n','dtopic__id','dtopic__title','score','share'))

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    context = {
        'run_id': run_id,
        'wtopics': wtopics,
        'dtopics': dtopics,
        'periods': periods,
        'stat': stat,
        'yts': yscores,
        'project': project,
        'user': request.user
    }
    return HttpResponse(template.render(context))

def highlight_dtm_w(request):

    dtid = int(request.GET.get('dtid',None))
    run_id = int(request.GET.get('run_id',None))

    stat = RunStats.objects.get(pk=run_id)

    wts = Topic.objects.filter(
        run_id=stat.parent_run_id,
        topicdtopic__dynamictopic=dtid
    ).order_by('-topicdtopic__score').values(
        'id',
        'topicdtopic__score'
    )

    ns = normalize([wts.values_list('topicdtopic__score',flat=True)])

    for i, w in enumerate(wts):
        w['score'] = ns[0][i]



    return HttpResponse(json.dumps(list(wts)))


##################################################################

def topic_presence_hlda(request):
    """
    View of main topic model page for hlda

    :param request:
    :return:
    """

    run_id = find_run_id(request.session)
    update_topic_titles_hlda(request.session)
    update_topic_scores(request.session)
    response = ''

    get_year_filter(request)


    presence_template = loader.get_template('tmv_app/topic_presence_hlda.html')

    topics = HTopic.objects.filter(run_id=run_id).order_by('-n_docs')
    max_score = topics[0].n_docs

    topic_tuples = []

    ttree = "{"

    for topic in topics:
        topic_tuples.append((topic, topic.n_docs, topic.n_docs/max_score*100))

    topics = topics.values()

    root = topics[0]
    root['children'] = []
    root['parent_id'] = "null"

    for topic in topics:
        if topic['parent_id']==root['topic']:
            topic['children'] = []
            for child in topics:
                if child['parent_id']==topic['topic']:
                    child['children'] = []
                    for grandchild in topics:
                        if grandchild['parent_id']==child['topic']:
                            child['children'].append(grandchild)
                    topic['children'].append(child)
            root['children'].append(topic)

    presence_page_context = {
        'topic_tuples': topic_tuples,
        'topic_tree': root
    }


    return HttpResponse(presence_template.render(presence_page_context))


def stats(request,run_id):
    """
    View with statistics of a model run

    :param request:
    :param run_id:
    :return:
    """

    template = loader.get_template('tmv_app/stats.html')

    stat = RunStats.objects.get(run_id=run_id)

    if stat.query:
        project = stat.query.project
    else:
        project = 'parliament'

    docs_seen = DocTopic.objects.filter(run_id=run_id).values('doc_id').order_by().distinct().count()

    stat.docs_seen = docs_seen

    if stat.query:
        stat.num_docs = stat.query.doc_set.count()
    elif stat.psearch:
        if stat.psearch.search_object_type == 1:
            stat.num_docs = stat.psearch.par_count
        else:
            stat.num_docs = stat.psearch.utterance_count

    stat.save()

    if stat.query:
        project = stat.query.project
    else:
        project = stat.psearch.project

    if request.method == "POST":
        topic_assessment=topicAssessmentForm(request.POST or None, max_value = stat.docs_seen)
        if topic_assessment.is_valid():
            uids = list(topic_assessment.cleaned_data["users"].values_list('pk',flat=True))
            n_docs = topic_assessment.cleaned_data["docs"]
            create_topic_assessments.delay(run_id, uids, n_docs)
        else:
            e = topic_assessment.errors
    else:
        topic_assessment=topicAssessmentForm(max_value = stat.docs_seen)

    topic_assessment.fields["users"].queryset = User.objects.filter(projectroles__project=project)
    topic_assessment.fields["docs"].min_value = 1

    wis = WordIntrusion.objects.filter(
        topic__run_id=run_id
    )

    tis = TopicIntrusion.objects.filter(
        intruded_topic__run_id=run_id
    )

    intr_dict = [
        {
            "intrusion": wis,
            "run_identifier": "topic__run_id",
            "title": "Word-Topic intrusions",
        },
        {
            "intrusion": tis,
            "run_identifier": "intruded_topic__run_id",
            "title": "Topic-Doc intrusions",
        }
    ]

    for intr in intr_dict:
        if intr["intrusion"].exists():
            intrusion_dict = {}
            intr["intrusion"] = intr["intrusion"].values(
                'score'
            ).annotate(
                n=Count('pk'),
            )

    #x = y

    context = {
        'run_id': run_id,
        'stat': stat,
        'num_topics': Topic.objects.filter(run_id=run_id).count(),
        'num_terms': Term.objects.filter(run_id=run_id).count(),
        'project': project,
        'user': request.user,
        'topic_assessment': topic_assessment,
        'intr_dict': intr_dict,
    }

    return HttpResponse(template.render(context, request))


def runs(request,pid=0):
    """
    View with list of all topic model runs

    :param request:
    :param pid:
    :return:
    """

    pid = int(pid)

    template = loader.get_template('tmv_app/runs.html')

    stats = RunStats.objects.all().order_by('-start')


    if pid > 0:
        stats_filtered = stats.filter(query__project_id=pid)

        if stats_filtered.count() <= 0:
            stats = stats.filter(psearch__project_id=pid)
        else:
            stats = stats_filtered


    stats = stats.annotate(
        dtopics = models.Count('dynamictopic', distinct=True),
        #terms = models.Count('term')
    )



    for s in stats:
        if s.parent_run_id is not None:
            run_id = s.parent_run_id
        else:
            run_id = s.run_id
        if s.max_topics is None and s.method=="DT":
            myear = Topic.objects.filter(run_id=run_id).aggregate(
                myear=models.Max('year')
            )['myear']
            s.max_topics = Topic.objects.filter(run_id=run_id,year=myear).count()
        if s.term_count is None or s.term_count==0:
            s.term_count = Term.objects.filter(run_id=run_id).count()
            s.save()

    context = {'stats':stats}

    return HttpResponse(template.render(context, request))

from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render

def update_run(request, run_id):
    try:
        stat = RunStats.objects.get(run_id=run_id)
        stat.notes = request.POST['notes']
        stat.save()
    except:
        pass

    return HttpResponseRedirect(reverse('tmv_app:runs'))

def delete_run(request,new_run_id):
    """
    Function to delete a run and its associated topic objects

    :param request:
    :param new_run_id:
    :return:
    """
    stat = RunStats.objects.get(run_id=new_run_id)

    if stat.query:
        p = stat.query.project
        if p is not None:
            pid = p.id
        else:
            pid = 0
    else:
        pid = 0

    stat.delete()
    topics = Topic.objects.filter(run_id_id=new_run_id)
    topics.delete()
    dt = DocTopic.objects.filter(run_id=new_run_id)
    dt.delete()
    tt = TopicTerm.objects.filter(run_id=new_run_id)
    tt.delete()
    ht = HTopic.objects.filter(run_id=new_run_id)
    ht.delete()
    DynamicTopic.objects.filter(run_id=new_run_id).delete()

    return HttpResponseRedirect(reverse('tmv_app:runs', kwargs={'pid': pid}))




def topic_random(request):
    return HttpResponseRedirect('/nacsos-legacy/tmv_app/topic/' + str(random.randint(1, Topic.objects.count())))

def doc_random(request,run_id):
    doc = random_doc(RunStats.objects.get(pk=run_id).query)
    return HttpResponseRedirect(
        reverse('tmv_app:doc_detail', kwargs={'run_id':run_id, 'doc_id':doc.pk})
    )

def term_random(request):
    return HttpResponseRedirect('/nacsos-legacy/tmv_app/term/' + str(random.randint(1, Term.objects.count())))
