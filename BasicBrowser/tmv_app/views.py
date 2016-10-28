from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, Context, RequestContext, loader
from tmv_app.models import *
from django.db.models import Q, F, Sum, Count, FloatField
from django.shortcuts import *
from django.forms import ModelForm
import random, sys, datetime
import urllib.request

# the following line will need to be updated to launch the browser on a web server
TEMPLATE_DIR = sys.path[0] + '/templates/'

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

nav_bar = loader.get_template('tmv_app/nav_bar.html').render()
global run_id

def find_run_id():
    settings = Settings.objects.all().first()
    run_id = settings.run_id
    return(run_id)

def show_toolbar(request):
    return True
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK" : show_toolbar,
}

def author_detail(request, author_name):
    run_id = find_run_id()
    response = author_name
    documents = Doc.objects.filter(docauthors__author=author_name,docauthors__run_id=run_id)

    topics = {}
    topics = Topic.objects.all()
    topics = []

    for d in documents:
        doctopics = d.doctopic_set.values()
        for dt in doctopics:
            if dt['scaled_score']*100 > 1 :  
                topic = Topic.objects.get(topic=dt['topic_id'])
                if topic in topics:
                    topics[topics.index(topic)].sum += dt['scaled_score']
                else:
                    topic.sum = dt['scaled_score']
                    topics.append(topic)

    topics = DocTopic.objects.filter(doc__docauthors__author=author_name, scaled_score__gt=0.01,run_id=run_id)

    topics = topics.annotate(total=(Sum('scaled_score')))

    topics = topics.values('topic','topic__title').annotate(
        tprop=Sum('scaled_score')
    ).order_by('-tprop')

    pie_array = []
    for t in topics:
        pie_array.append([t['tprop'], '/topic/' + str(t['topic']), 'topic_' + str(t['topic'])])

    author_template = loader.get_template('tmv_app/author.html')

    author_page_context = Context({'nav_bar': nav_bar, 'author': author_name, 'docs': documents, 'topics': topics, 'pie_array': pie_array})

    return HttpResponse(author_template.render(author_page_context))

def index(request):
    ip = request.META['REMOTE_ADDR']
    return HttpResponse("Hello, " + str(ip) + " You're at the topic browser index.")




###########################################################################
## Topic View
def topic_detail(request, topic_id):    
    #update_topic_titles()
    response = ''
    run_id = find_run_id()
    topic_template = loader.get_template('tmv_app/topic.html')
    
    topic = Topic.objects.get(topic=topic_id,run_id=run_id)
    #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')
    topicterms = Term.objects.filter(topicterm__topic=topic.topic,run_id=run_id).order_by('-topicterm__score')
    doctopics = Doc.objects.filter(doctopic__topic=topic.topic).order_by('-doctopic__scaled_score')[:50]
    
    terms = []
    term_bar = []
    remainder = 1
    remainder_titles = ''
    
    for tt in topicterms:
        term = Term.objects.get(term=tt.term)
        score = tt.topicterm_set.all()[0].score
        
        terms.append(term)
        if score >= .01:
            term_bar.append((True, term, score * 100))
            remainder -= score
        else:
            if remainder_titles == '':
                remainder_titles += term.title
            else:
                remainder_titles += ', ' + term.title
    term_bar.append((False, remainder_titles, remainder*100))
       
    docs = []
    for dt in doctopics:
        docs.append(Doc.objects.get(doc=dt.doc))

    #update_year_topic_scores()

    all_docs = []

    yts = TopicYear.objects.all()

    for yt in yts:
        yt.topic_title = yt.topic.title

    

    ytarray = list(yts.values('PY','count','score','topic_id','topic__title'))
  
    topic_page_context = Context({'nav_bar': nav_bar, 'topic': topic, 'terms': terms, 'term_bar': term_bar, 'docs': docs, 'yts': ytarray, 'all_docs': all_docs})
    
    return HttpResponse(topic_template.render(topic_page_context))

##############################################################

def term_detail(request, term_id):
    update_topic_titles()
    run_id = find_run_id()
    response = ''

    term_template = loader.get_template('tmv_app/term.html')
    
    term = Term.objects.get(term=term_id,run_id=run_id)
    
    topics = {}
    for topic in Topic.objects.filter(run_id=run_id):
        tt = TopicTerm.objects.filter(topic=topic.topic, term=term_id,run_id=run_id)
        if len(tt) > 0:
            topics[topic] = tt[0].score
    
    sorted_topics = sorted(topics.keys(), key=lambda x: -topics[x])
    topic_tuples = []

    
    if len(topics.keys()) > 0:
        max_score = max(topics.values())
        for topic in sorted_topics:
            topic_tuples.append((topic, topics[topic], topics[topic]/max_score*100))

    topics = TopicTerm.objects.filter(term=term_id,run_id=run_id).order_by('-score')
    if len(topics) > 0:
        topic_tuples = []
        max_score = topics[0].score
        for topic in topics:
            topic_tuples.append((topic.topic, topic.score, topic.score/max_score*100))
    

    term_page_context = Context({'nav_bar': nav_bar, 'term': term, 'topic_tuples': topic_tuples})
    
    return HttpResponse(term_template.render(term_page_context))

def doc_detail(request, doc_id):
    run_id = find_run_id()
    update_topic_titles()
    response = ''
    print ( "doc: " + str(doc_id) )
    doc_template = loader.get_template('tmv_app/doc.html')
    
    doc = Doc.objects.get(doc=doc_id)
    doctopics = DocTopic.objects.filter(doc=doc_id,run_id=run_id).order_by('-score')

    doc_authors = DocAuthors.objects.filter(doc__doc=doc_id,run_id=run_id)

    topics = []
    pie_array = []
    dt_threshold = Settings.objects.get(id=1).doc_topic_score_threshold
    print ( dt_threshold )
    dt_thresh_scaled = Settings.objects.get(id=1).doc_topic_scaled_score
    topicwords = {}
    ntopic = 0
    for dt in doctopics:
        if ((not dt_thresh_scaled and dt.score >= dt_threshold) or (dt_thresh_scaled and dt.scaled_score*100 >= dt_threshold)):
            topic = Topic.objects.get(topic=dt.topic_id)
            ntopic+=1
            topic.ntopic = "t"+str(ntopic)
            topics.append(topic)
            terms = Term.objects.filter(topicterm__topic=topic.topic).order_by('-topicterm__score')[:10]
            
            topicwords[ntopic] = []
            for tt in terms:
                topicwords[ntopic].append(tt.title)
            print ( topic.title )
            if not dt_thresh_scaled:
                pie_array.append([dt.score, '/topic/' + str(topic.topic), 'topic_' + str(topic.topic)])
            else:
                pie_array.append([dt.scaled_score, '/topic/' + str(topic.topic), 'topic_' + str(topic.topic)])
        else:
            print ( (dt.score, dt.scaled_score) )
   
    words = []
    for word in doc.content.split():
        wt = ""
        for t in range(1,ntopic+1):
            if word in topicwords[t]:
                wt = t
        words.append({'title': word, 'topic':"t"+str(wt)})
    
    doc_page_context = Context({'nav_bar': nav_bar, 'doc': doc, 'topics': topics, 'pie_array': pie_array,'doc_authors': doc_authors, 'words': words })
    
    return HttpResponse(doc_template.render(doc_page_context))

def topic_list_detail(request):
    run_id = find_run_id()
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

    list_page_context = Context({'nav_bar': nav_bar, 'rows': rows})
    
    return HttpResponse(list_template.render(list_page_context))

#################################################################
### Main page!
def topic_presence_detail(request):
    run_id = find_run_id()
    update_topic_titles()
    update_topic_scores()
    response = ''
    
    presence_template = loader.get_template('tmv_app/topic_presence.html')

    topics = Topic.objects.filter(run_id=run_id).order_by('-score')
    max_score = topics[0].score

    topic_tuples = []
    for topic in topics:
        topic_tuples.append((topic, topic.score, topic.score/max_score*100))

    presence_page_context = Context({'nav_bar': nav_bar, 'topic_tuples': topic_tuples})
    
    return HttpResponse(presence_template.render(presence_page_context))


def stats(request):
    run_id = find_run_id()

    stats_template = loader.get_template('tmv_app/stats.html')

    nav_bar = loader.get_template('tmv_app/nav_bar.html')

    topics_seen = DocTopic.objects.distinct('doc_id').count()

    stats = RunStats.objects.get(run_id=run_id)

    stats_page_context = Context({'nav_bar': nav_bar, 'num_docs': Doc.objects.count(),'topics_seen': topics_seen, 'num_topics': Topic.objects.count(), 'num_terms': Term.objects.count(), 'start_time': stats.start, 'elapsed_time': stats.start, 'num_batches': stats.batch_count, 'last_update': stats.last_update})


    return HttpResponse(stats_template.render(stats_page_context))

def runs(request):
    run_id = find_run_id()

    runs_template = loader.get_template('tmv_app/runs.html')

    nav_bar = loader.get_template('tmv_app/nav_bar.html')

    topics_seen = DocTopic.objects.distinct('doc_id').count()

    stats = RunStats.objects.all().order_by('-start')

    for stat in stats:
        stat_run_id = stat.run_id
        stat.topics = Topic.objects.filter(run_id=stat_run_id).count()
        stat.documents = Doc.objects.filter(run_id=stat_run_id).count()
        stat.terms = Term.objects.filter(run_id=stat_run_id).count()

    runs_page_context = Context({'nav_bar': nav_bar, 'stats':stats, 'run_id':run_id})


    return HttpResponse(runs_template.render(runs_page_context))

class SettingsForm(ModelForm):
    class Meta:
        model = Settings
        fields = '__all__'

def settings(request):
    run_id = find_run_id()

    settings_template = loader.get_template('tmv_app/settings.html')
   
    settings_page_context = Context({'nav_bar': nav_bar, 'settings': Settings.objects.get(id=1)})

    return HttpResponse(settings_template.render(settings_page_context))
    #return render_to_response('settings.html', settings_page_context, context_instance=RequestContext(request))

def apply_settings(request):
    settings = Settings.objects.get(id=1)
    print ( settings.doc_topic_score_threshold )
    print ( settings.doc_topic_scaled_score )
    form = SettingsForm(request.POST, instance=settings)
    print ( form )
    print ( settings )
    #TODO: add in checks for threshold (make sure it's a float)
    settings.doc_topic_score_threshold = float(request.POST['threshold'])
   
    print ( settings.doc_topic_score_threshold )
    print ( settings.doc_topic_scaled_score )
    settings.save()

    return HttpResponseRedirect('/topic_list')

def apply_run_filter(request,new_run_id):
    settings = Settings.objects.get(id=1)
    settings.run_id = new_run_id
    settings.save()

    return HttpResponseRedirect('/tmv_app/runs')

def update_topic_titles():
    run_id = find_run_id()
    stats = RunStats.objects.get(run_id=run_id)
    #if not stats.topic_titles_current:
    if "a" in "ab":
        for topic in Topic.objects.filter(run_id=run_id):
            #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')[:3]
            topicterms = Term.objects.filter(topicterm__topic=topic.topic).order_by('-topicterm__score')[:3]
            if topicterms.count() < 3:
                continue
            
            new_topic_title = '{' + topicterms[0].title + ', ' + topicterms[1].title + ', ' + topicterms[2].title + '}'

            topic.title = new_topic_title
            topic.save()
        stats.topic_titles_current = True
        stats.save()


def update_topic_scores():
    run_id = find_run_id()
    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_scores_current:
        for topic in Topic.objects.all():
            score = sum([dt.score for dt in DocTopic.objects.filter(topic=topic.topic)])
            topic.score = score
            topic.save()
        stats.topic_scores_current = True
        stats.save()

def update_year_topic_scores():
    run_id = find_run_id()
    stats = RunStats.objects.get(id=1)
    #if "a" in "a":    
    if not stats.topic_year_scores_current:
        yts = DocTopic.objects.all()
        yts = DocTopic.objects.filter(doc__PY__gt=1989)  

        yts = yts.values('doc__PY').annotate(
            yeartotal=Sum('scaled_score')
        )

        ytts = yts.values().values('topic','topic__title','doc__PY').annotate(
            score=Sum('scaled_score')
        )


        for ytt in ytts:
            yttyear = ytt['doc__PY']
            topic = Topic.objects.get(topic=ytt['topic'])
            for yt in yts:
                ytyear = yt['doc__PY']
                if yttyear==ytyear:
                    yeartotal = yt['yeartotal']
            try:
                topicyear = TopicYear.objects.get(topic=topic,PY=yttyear)
            except:
                topicyear = TopicYear(topic=topic,PY=yttyear)
            topicyear.score = ytt['score']
            topicyear.count = yeartotal
            topicyear.save()

        stats.topic_year_scores_current = True
        stats.save()
        

def topic_random(request):
    return HttpResponseRedirect('/tmv_app/topic/' + str(random.randint(1, Topic.objects.count())))

def doc_random(request):
    return HttpResponseRedirect('/tmv_app/doc/' + str(random.randint(1, Doc.objects.count())))

def term_random(request):
    return HttpResponseRedirect('/tmv_app/term/' + str(random.randint(1, Term.objects.count())))

def get_doc_display(doc):
    url = "http://en.wikipedia.org/wiki/" + doc.title
    url2 = "http://en.wikipedia.org/wiki/" + doc.title.replace(" ", "_").replace("&amp;", '&')
    
    f = ''
    try:
        f = opener.open(url.encode('utf-8'))
    except urllib.request.HTTPError:
        try:
            f = opener.open(url2)
        except:
            return "This page could not be found."
    site = f.read()
    
    # get past the unwanted content at the start of the html file
    end_cur = site.find('</h1>')

    start_cur = site[end_cur:].find('<table class="vertical-navbox nowraplinks"')
    while (start_cur != -1):
        while (start_cur != -1):
            new_end_cur = end_cur + start_cur + site[end_cur + start_cur:].find('</table>')
            start_cur = site[end_cur + start_cur + len('<table') : new_end_cur].find('<table')
            end_cur = new_end_cur
        start_cur = site[end_cur:].find('<table class="vertical-navbox nowraplinks"')

    # cherrypick desired content, up to a certain length
    new_start_cur = site[end_cur:].find('<p')
    new_end_cur = site[end_cur:].find('</p>')

    pair_key = 0
    pairs = [('<p', '</p>'), ('<span class="mw-headline"', '</span>'), ('<div id="toctitle">', '</div>'), ('<ul>','</ul>')]

    content = ''
    while (new_start_cur != -1 and new_end_cur != -1 and len(content) < 5000):
        content_addition = site[end_cur+new_start_cur:end_cur+new_end_cur+len(pairs[pair_key][1])]
        if pair_key == 1:
            content += '\n<h3>' + content_addition + '</h3>'
        else:
            content += '\n' + content_addition

        end_cur = end_cur + new_end_cur + len(pairs[pair_key][1])
        
        new_start_cur = -1
        new_end_cur = -1
        for pair in pairs:
            start_cur = site[end_cur:].find(pair[0])
            if start_cur != -1 and (new_start_cur == -1 or start_cur < new_start_cur):
                new_start_cur = start_cur
                new_end_cur = site[end_cur:].find(pair[1])
                temp_start_cur = new_start_cur
                count = 0
                while count <10 and site[end_cur + temp_start_cur + len(pair[0]) : end_cur + new_end_cur].find(pair[0]) != -1:
                    temp_start_cur = temp_start_cur + site[end_cur + temp_start_cur + len(pair[0]):].find(pair[0]) + len(pair[0])
                    new_end_cur = new_end_cur + site[end_cur + new_end_cur + len(pair[1]):].find(pair[1])  + len(pair[1])
                    count += 1
                pair_key = pairs.index(pair)
    
    # make sure links connect to wikipedia.org properly
    content = unicode(content, errors='ignore')
    content = content.replace('href="/wiki', 'href="http://www.wikipedia.org/wiki')
    content = content.replace(u'href="#', 'href="' + url + '#')
    content = content.replace("\n\n", "</p>\n\n<p>")
    
    return content
