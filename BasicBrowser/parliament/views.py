from django.shortcuts import render
from django.template import loader, RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django_tables2.config import RequestConfig
from django.db.models import Q, Count, Func, F, Sum, Value, Case, When, IntegerField
from parliament.models import *
from .tables import *
from .forms import *
from .tasks import *
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
import datetime
# Create your views here.
@login_required
def index(request):

    template = loader.get_template('parliament/index.html')

    parls = Parl.objects.all()
    parls = ParlTable(parls, order_by="id")

    docs = Document.objects.all()

    context = {
        'docs': docs,
        'parls': parls,
    }

    return HttpResponse(template.render(context, request))

def person_table(persons):
    persons = persons.annotate(
        contributions=Count('utterance'),
        words = Sum('utterance__paragraph__word_count'),
        applauded = Sum(
            Case(
                When(utterance__paragraph__interjection__type=Interjection.APPLAUSE,then=1),
                default=0,
                output_field=IntegerField()
            )

        )
    )
    persons = PersonTable(persons)
    return persons

@login_required
def parliament(request,pid):

    template = loader.get_template('parliament/parliament.html')

    parl = Parl.objects.get(pk=pid)
    ps  = ParlSession.objects.filter(parliament=parl).annotate(
        docs = Count('document')
    )
    ps = ParlSessionTable(ps, order_by="id")

    persons = person_table(Person.objects.filter(
        utterance__document__parlsession__parliament=parl,
    ))

    RequestConfig(request).configure(persons)

    parties = Party.objects.filter(parliament=parl).annotate(
        members=Count('person')
    )

    parties = PartyTable(parties)


    context = {
        'ps': ps,
        'parl': parl,
        'persons': persons,
        'parties': parties
    }

    return HttpResponse(template.render(context, request))


@login_required
def psession(request,pid):

    template = loader.get_template('parliament/psession.html')

    ps  = ParlSession.objects.get(pk=pid)

    docs = Document.objects.filter(parlsession=ps).order_by('date')
    docs = DocumentTable(docs)
    RequestConfig(request).configure(docs)

    context = {
        'docs': docs,
        'ps': ps,
    }

    return HttpResponse(template.render(context, request))

@login_required
def document(request,did,page=1):

    template = loader.get_template('parliament/document.html')

    doc = Document.objects.get(pk=did)

    perpage=5

    context = {
        'uts': doc.utterance_set.all().order_by('id').prefetch_related(
            'paragraph_set',
            'paragraph_set__interjection_set',
            'speaker',
            'paragraph_set__interjection_set__persons',
            'paragraph_set__interjection_set__parties',
        ),
        'document': doc
    }

    return HttpResponse(template.render(context, request))


@login_required
def search(request):

    template = loader.get_template('parliament/search.html')

    if request.method=="POST":
        sf = SearchForm(request.POST)
        if sf.is_valid():
            s = sf.save(commit=False)
            s.creator=request.user
            s.save()
            do_search.delay(s.id)

    searchform = SearchForm()

    searches = SearchTable(Search.objects.all())

    context = {
        'searchform': searchform,
        'searches': searches
    }

    return HttpResponse(template.render(context, request))

@login_required
def search_pars(request,sid):

    template = loader.get_template('parliament/search-pars.html')

    s = Search.objects.get(pk=sid)
    pars = Paragraph.objects.filter(search_matches=s)
    pt = SearchParTable(pars)
    pt.reg_replace(s.text)
    RequestConfig(request).configure(pt)

    context = {
        'pars': pt
    }

    return HttpResponse(template.render(context, request))


@login_required
def search_home(request,sid):
    template = loader.get_template('parliament/search-home.html')

    s = Search.objects.get(pk=sid)
    pars = Paragraph.objects.filter(search_matches=s)

    graph = list(pars.filter(utterance__document__date__isnull=False).order_by().annotate(
        year=TruncMonth('utterance__document__date')
    ).order_by('year').values('year').annotate(n = Count('id')))

    for i in range(len(graph)):
        graph[i]['year']=graph[i]['year'].strftime('%Y-%m')

    stat = RunStats.objects.filter(psearch=s).last()
    if stat is None:
        topics = None
    else:
        topics = stat.topic_set.all()

    context = {
        'pars': pars,
        'graph': list(graph),
        's': s,
        'x': 'year',
        'y': 'n',
        'stat': stat,
        'topics': topics
    }
    return HttpResponse(template.render(context, request))

@login_required
def parl_topic(request,tid):
    template = loader.get_template('parliament/parl-topic.html')

    topic = Topic.objects.get(pk=tid)
    stat = topic.run_id
    s = stat.psearch
    pars = Paragraph.objects.filter(
        search_matches=s,doctopic__topic=topic
    ).order_by(
        '-doctopic__score'
    )

    pt = SearchParTable(pars)

    pt.reg_replace("|".join([s.text]+[x for x in topic.top_words]))
    RequestConfig(request).configure(pt)

    stat = RunStats.objects.filter(psearch=s).last()
    topics = stat.topic_set.all()

    context = {
        'pars': pt,
        's': s,
        'x': 'year',
        'y': 'n',
        'stat': stat,
        'topic': topic
    }
    return HttpResponse(template.render(context, request))

@login_required
def person(request,tid):

    template = loader.get_template('parliament/person.html')
    p = Person.objects.get(pk=tid)
    pars = Paragraph.objects.filter(utterance__speaker=p)
    pt = SearchParTable(pars)
    RequestConfig(request).configure(pt)

    seats = Seat.objects.filter(occupant=p)

    context = {
        'p':p,
        'pars': pt,
        'seats': seats
    }

    return HttpResponse(template.render(context, request))

@login_required
def party(request,tid):

    template = loader.get_template('parliament/party.html')

    party = Party.objects.get(pk=tid)

    persons = person_table(Person.objects.filter(
        party=party
    ))
    RequestConfig(request).configure(persons)

    pars = Paragraph.objects.filter(utterance__speaker__party=party)
    pt = SearchParTable(pars)
    RequestConfig(request).configure(pt)



    context = {
        'party': party,
        'persons': persons,
        'pars': pt
    }

    return HttpResponse(template.render(context, request))
