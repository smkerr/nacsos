
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Template, Context, RequestContext, loader
from tmv_app.models import *
from scoping.models import *
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

# the following line will need to be updated to launch the browser on a web server
TEMPLATE_DIR = sys.path[0] + '/templates/'

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

global run_id

def find_run_id(request):
    try:
        run_id = request['run_id']
    except:
        settings = Settings.objects.all().first()
        run_id = settings.run_id
        try:
            request['run_id'] = run_id
        except:
            pass
    return(int(run_id))

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

    documents = Doc.objects.filter(docauthinst__AU=author_name).distinct()

    dt_threshold = Settings.objects.get(id=1).doc_topic_score_threshold

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

def network(request,run_id):
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
    nodes = json.dumps(list(nodes),indent=4,sort_keys=True)
    links = topiccorrs.objects.filter(run_id=run_id).filter(score__gt=0.05,score__lt=1,ar=ar).annotate(
        source=F('topic'),
        target=F('topiccorr')
    )
    links = json.dumps(list(links.values('source','target','score')),indent=4,sort_keys=True)
    context = {
        "nodes":nodes,
        "links":links,
        "run_id":run_id,
        "stat": RunStats.objects.get(pk=run_id)
    }

    return HttpResponse(template.render(context, request))

def return_corrs(request):
    cor = float(request.GET.get('cor',None))
    run_id = int(request.GET.get('run_id',None))
    ar = int(request.GET.get('ar',None))
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
## DynamicTopic View
def dynamic_topic_detail(request,topic_id):
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
        #if t.top_words is not None:
        if "x" is "y":
            t.tts = t.top_words
        else:
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

    docs = docs.annotate(
        topic_combination = F('score') * F('topic__topicdtopic__score')
    ).order_by('-topic_combination')[:50].values(
        'doc__pk','doc__PY','doc__title','topic_combination'
    )

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


    context = {
        'project': stat.query.project,
        'stat': stat,
        'run_id': run_id,
        'topic': topic,
        'topicterms': topicterms,
        'wtopics': wtopics,
        'wtvs': list(dtopics.values('title','score','year','dscore','id')),
        'ysums': list(ysums.values('year','sum')),
        'docs': docs,
        'ytterms': ytterms,
        'yscores': yscores
    }
    return HttpResponse(template.render(request =request, context=context))

def dtopic_detail(request,topic_id):
    template = loader.get_template('tmv_app/dtopic.html')

    topic = Topic.objects.get(pk=topic_id)

    tterms = []
    tts = TopicTerm.objects.filter(topic=topic)
    for py in tts.distinct('PY') \
        .order_by('PY').values_list('PY',flat=True):
        ytts = tts.filter(PY=py).order_by('-score')[:10]
        tterms.append(ytts)

    docs = Doc.objects.filter(doctopic__topic=topic) \
        .order_by('-doctopic__score')[:50]

    context = {
        "topic":topic,
        "tterms": tterms,
        "docs": docs
    }

    return HttpResponse(template.render(context))




###########################################################################
## Topic View
def topic_detail(request, topic_id, run_id=0):

    template = loader.get_template('tmv_app/topic.html')

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

    topic_template = loader.get_template('tmv_app/topic.html')

    topic = Topic.objects.get(pk=topic_id,run_id=stat.parent_run_id)

    topicterms = Term.objects.filter(
        topicterm__topic=topic, #run_id=stat.parent_run_id,
        topicterm__score__gt=0.00001
    ).order_by('-topicterm__score')[:50]

    if Settings.objects.first().doc_topic_scaled_score==True:
        doctopics = Doc.objects.filter(
            doctopic__topic=topic,doctopic__run_id=run_id
        ).order_by('-doctopic__scaled_score')[:50]
    else:
        doctopics = Doc.objects.filter(
            doctopic__topic=topic,doctopic__run_id=run_id
        ).order_by('-doctopic__score')[:50]

    ndocs = Doc.objects.filter(
        doctopic__topic=topic,
        doctopic__run_id=run_id,
        doctopic__score__gt=stat.dthreshold
    ).count()

    doctopics = doctopics.values('PY','title','pk','doctopic__score')
    terms = []
    term_bar = []
    remainder = 1
    remainder_titles = ''

    for tt in topicterms:
        term = Term.objects.get(pk=tt.pk)
        score = tt.topicterm_set.all()[0].score

        terms.append(term)
        if score >= .00001:
            term_bar.append((True, term, score * 100))
            remainder -= score
        else:
            if remainder_titles == '':
                remainder_titles += term.title
            else:
                remainder_titles += ', ' + term.title
    term_bar.append((False, remainder_titles, remainder*100))

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
    dtops = TopicDTopic.objects.filter(
        topic=topic_id,
        dynamictopic__run_id=run_id
    ).order_by('-score')[:10]

    ### Journals
    journals = JournalAbbrev.objects.filter(
        doc__doctopic__topic=topic,
        doc__journal__isnull=False,
        doc__doctopic__score__gt=stat.dthreshold
    ).values('fulltext').annotate(
        t = Count('doc__doctopic__score')
    ).order_by('-t')[:10]

    topic_page_context = {
        'topic': topic,
        'terms': terms,
        'term_bar': term_bar,
        'docs': doctopics,
        'yts': ytarray,
        'corrtops': corrtops,
        'dtops': dtops,
        'run_id': run_id,
        'stat': stat,
        'journals': journals,
        'ndocs': ndocs
        }

    return HttpResponse(topic_template.render(topic_page_context))

def get_topic_docs(request,topic_id):

    template = loader.get_template('tmv_app/topic_docs.html')
    topic = Topic.objects.get(pk=topic_id)
    run_id = topic.run_id.pk

    stat = RunStats.objects.get(run_id=run_id)

    dt_threshold = stat.dthreshold
    dt_thresh_scaled = Settings.objects.get(id=1).doc_topic_scaled_score
    if stat.method=="BD":
        dt_threshold=dt_threshold*100

    svalue = request.GET.get('sort',None)
    sortcol = svalue.replace('-','')



    doctopics = Doc.objects.filter(
        doctopic__topic=topic,doctopic__run_id=run_id,
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

    #x = y
    context = {
        "docs": doctopics,
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

    #x = y
    nodes = json.dumps(nodes,indent=4,sort_keys=True)
    links = tc.objects.filter(run_id=run_id).filter(
        score__gt=t,
        score__lt=1,
        ar=ar
    ).annotate(
        source=F('topic'),
        target=F('topiccorr')
    )
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
## Doc view

def doc_detail(request, doc_id, run_id):

    snowball_stemmer = SnowballStemmer("english")


    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(doc_detail_hlda(request, doc_id))
    update_topic_titles(int(run_id))
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
    dt_threshold = Settings.objects.get(id=1).doc_topic_score_threshold
    dt_thresh_scaled = Settings.objects.get(id=1).doc_topic_scaled_score
    if stat.dthreshold is not None:
        dt_threshold = stat.dthreshold
        #dt_thresh_scaled = stat.dthreshold


    if stat.method=="BD":
        dt_threshold=dt_threshold*100
    topicwords = {}
    ntopic = 0

    if dt_thresh_scaled:
        doctopics = doctopics.filter(scaled_score__gte=dt_threshold/80)
    else:
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
            pie_array.append([dt.score, '/tmv_app/topic/' + str(topic.pk), 'topic_' + str(topic.pk)])
        else:
            pie_array.append([dt.scaled_score, '/tmv_app/topic/' + str(topic.pk), 'topic_' + str(topic.pk)])


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
        'kwp': kwp

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
        ).order_by('-topicterm__score')[:5].values_list('title',flat=True))
        t.terms = "; ".join(termlist)
        t.mtd = t.score/tsum['tsum']*100

    writer = csv.writer(response,delimiter=',')
    writer.writerow(['sep=,'])

    writer.writerow(["Topic ID","Topic Name","Stemmed Keywords","Marginal Topic Distribution"])

    for t in topics:
        row = [t.pk,"",t.terms,t.mtd]
        writer.writerow(row)

    return response

def topic_list_detail(request):
    run_id = find_run_id(request.session)
    update_topic_titles()
    response = ''

    template_file = open(TEMPLATE_DIR + 'topic_list.html', 'r')
    list_template = Template(template_file.read())

    topics = Topic.objects.all()

    terms = []
    for t in topics:
        topicterms = TopicTerm.objects.filter(topic=t.topic).order_by('-score')[:5]
        temp =[]
        term_count = 5
        for tt in topicterms:
            temp.append(Term.objects.get(term=tt.term))
            term_count -= 1
        for i in range(term_count):
            temp.append(None)
        terms.append(temp)

    div_topics = []
    div_terms = []
    rows = []
    n = 3
    for i in xrange(0, len(topics), n):
        temp = []
        for j in range(5):
            K = min(len(topics), i+n)
            t = [terms[k][j] for k in range(i,K,1)]
            while len(t) < n:
                t.append(None)
            temp.append(t)
        tops = topics[i:i+n]
        while len(tops) < n:
            tops.append(None)
        rows.append((tops, temp))

    list_page_context = {'rows': rows}

    return HttpResponse(list_template.render(list_page_context))

#################################################################
### Main page!
def topic_presence_detail(request,run_id):
    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(topic_presence_hlda(request))

    if stat.method == "DT":
        update_dtopics(run_id)
        return dtm_home(request,run_id)
    if stat.method == "BD":
        update_bdtopics(run_id)


    run_id = int(run_id)

    update_topic_titles(run_id)
    update_topic_scores(run_id)


    response = ''

    get_year_filter(request)

    presence_template = loader.get_template('tmv_app/topic_presence.html')
    if stat.method=="DT":
        topics = DynamicTopic.objects.filter(run_id=run_id).order_by('-score')
    else:
        topics = Topic.objects.filter(run_id=run_id).order_by('-score')
    max_score = topics[0].score

    topic_tuples = []
    for topic in topics:
        s = topic.score
        topic_tuples.append((topic, topic.score, topic.score/max_score*100))

    presence_page_context = {
        'run_id': run_id,
        'topic_tuples': topic_tuples,
        'stat': stat
    }

    return HttpResponse(presence_template.render(presence_page_context))

def dtm_home(request, run_id):
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


    context = {
        'run_id': run_id,
        'wtopics': wtopics,
        'dtopics': dtopics,
        'periods': periods,
        'stat': stat,
        'yts': yscores
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
## Alt Main page for hlda

def topic_presence_hlda(request):
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

    template = loader.get_template('tmv_app/stats.html')

    stats = RunStats.objects.get(run_id=run_id)

    docs_seen = DocTopic.objects.filter(run_id=run_id).values('doc_id').order_by().distinct().count()

    stats.docs_seen = docs_seen
    stats.num_docs = stats.query.doc_set.count()

    stats.save()

    context = {
        'stats': stats,
        'num_topics': Topic.objects.filter(run_id=run_id).count(),
        'num_terms': Term.objects.filter(run_id=run_id).count(),
    }

    return HttpResponse(template.render(context))


def runs(request,pid=0):

    pid = int(pid)

    template = loader.get_template('tmv_app/runs.html')

    stats = RunStats.objects.all().order_by('-start')


    if pid > 0:
        stats = stats.filter(query__project_id=pid)


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

class SettingsForm(ModelForm):
    class Meta:
        model = Settings
        fields = '__all__'

def queries(request):

    return HttpResponse("bla")

def settings(request):
    run_id = find_run_id(request)

    settings_template = loader.get_template('tmv_app/settings.html')

    settings_page_context = {
        'settings': Settings.objects.get(id=1)
    }

    return HttpResponse(settings_template.render(settings_page_context,request))
    #return render_to_response('settings.html', settings_page_context, context_instance=RequestContext(request))

def apply_settings(request):
    settings = Settings.objects.get(id=1)
    form = SettingsForm(request.POST, instance=settings)
    #TODO: add in checks for threshold (make sure it's a float)
    settings.doc_topic_score_threshold = float(request.POST['doc_topic_score_threshold'])
    try:
        scaled = request.POST['doc_topic_scaled_score']
        scaled = True
    except:
        scaled = False
    settings.doc_topic_scaled_score = scaled
    settings.save()

    return HttpResponseRedirect(reverse('tmv_app:topics'))

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

def apply_run_filter(request,new_run_id):
#    settings = Settings.objects.get(id=1)
#    settings.run_id = new_run_id
#    settings.save()
    request.session['run_id'] = new_run_id

    return HttpResponseRedirect('/tmv_app/runs')

def delete_run(request,new_run_id):
    stat = RunStats.objects.get(run_id=new_run_id)

    p = stat.query.project
    if p is not None:
        pid = p.id
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
    return HttpResponseRedirect('/tmv_app/topic/' + str(random.randint(1, Topic.objects.count())))

def doc_random(request,run_id):
    doc = random_doc(RunStats.objects.get(pk=run_id).query)
    return HttpResponseRedirect(
        reverse('tmv_app:doc_detail', kwargs={'run_id':run_id, 'doc_id':doc.pk})
    )

def term_random(request):
    return HttpResponseRedirect('/tmv_app/term/' + str(random.randint(1, Term.objects.count())))
