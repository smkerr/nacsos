from django.shortcuts import render
from django.template import loader, RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django_tables2.config import RequestConfig
from django.db.models import Q, Count, Func, F, Sum, Value, Case, When, IntegerField
from .models import *
import twitter.models as tm
from .tables import *
from .forms import *
from .tasks import *
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
import datetime


# Create your views here.
@login_required
def index(request):
    """
    Displays all available parliaments

    **Template:**

    :template:`parliament/index.html`
    """

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
    """
    Summarises actions of :model:`parliament.Person` in a parliament

Todo:
    * Move to utils
    """
    persons = persons.annotate(
        contributions=Count('utterance'),
        words=Sum('utterance__paragraph__word_count'),
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
    """
    Displays Parliament information

    Displays information on :model:`parliament.ParlPeriod`, :model:`parliament.Party`, and :model:`parliament.Person` for each parliament :model:`parliament.Parl`

    **Context**

    ``ps``
        A table displaying all parliamentary periods and associated documents

    ``parl``
        An instance of :model:`parliament.Parl`

    ``persons``
        A table displaying all parliamentarians in :model:`parliament.Parl`

    ``parties``
        A table displaying all political parties in :model:`parliament.Parl` and number of parliamentarians in each party

    **Template:**

    :template:`parliament/parliament.html`
    """

    template = loader.get_template('parliament/parliament.html')

    parl = Parl.objects.get(pk=pid)
    ps  = ParlPeriod.objects.filter(parliament=parl).annotate(
        docs = Count('document')
    ).order_by('n')
    ps = ParlPeriodTable(ps, order_by="n")

    # persons = person_table(Person.objects.filter(
    #     utterance__document__parlperiod__parliament=parl,
    # ))
    persons = person_table(Person.objects.filter(
        seat__parlperiod__parliament=parl
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
def parlperiod(request,pid):
    """
    Displays documents from one parliamentary period

    **Context**

    ``ps``
        An instance of :model:`parliament.ParlPeriod`

    ``docs``
        A table displaying the documents in :model:`parliament.ParlPeriod`

    **Template:**

    :template:`parliament/parlperiod.html`
    """

    template = loader.get_template('parliament/parlperiod.html')

    ps  = ParlPeriod.objects.get(pk=pid)

    docs = Document.objects.filter(parlperiod=ps).order_by('date')
    docs = DocumentTable(docs)
    RequestConfig(request).configure(docs)

    context = {
        'docs': docs,
        'ps': ps,
    }

    return HttpResponse(template.render(context, request))


@login_required
def document(request,did,page=1):
    """
    Displays content of document, comprising speeches in parliament

    **Context**

    ``uts``
        Displays all :model:`parliament.Utterance` objects associated with one document

    ``document``
        An instance of :model:`parliament.Document`

    **Template:**

    :template:`parliament/document.html`
    """

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
def utterance(request, ut_id):
    """
    Displays utterance (speech) from one document

    **Context**

    ``uts``
        Displays all :model:`parliament.Paragraph` objects associated with one utterance

    ``document``
        An instance of :model:`parliament.Document`

    ``ut_id``
        Identification number associated with utterance

    **Template:**

    :template:`parliament/document.html`
    """

    template = loader.get_template('parliament/utterance.html')

    uts = Utterance.objects.filter(id=ut_id)

    context = {
        'uts': uts.prefetch_related(
            'paragraph_set',
            'paragraph_set__interjection_set',
            'speaker',
            'paragraph_set__interjection_set__persons',
            'paragraph_set__interjection_set__parties',
        ),
        'document': uts.first().document,
        'ut_id': ut_id
    }

    return HttpResponse(template.render(context, request))


@login_required
def paragraph(request, par_id):
    """
    Displays paragraph from one utterance (speech)

    **Context**

    ``par``
        An instance of :model:`parliament.Paragraph`

    ``speaker``
        Associated speaker, :model:`parliament.Person` with paragraph

    ``document``
        Associated document, :model:`parliament.Document` with paragraph

    ``utterance``
        Associated utterance, :model:`parliament.Utterance` with paragraph

    **Template:**

    :template:`parliament/paragraph.html`
    """

    template = loader.get_template('parliament/paragraph.html')

    par = Paragraph.objects.get(id=par_id)

    context = {
        'par': par,
        'speaker': par.utterance.speaker,
        'document': par.utterance.document,
        'utterance': par.utterance,
        'par_id': par_id
    }

    return HttpResponse(template.render(context, request))


# list of all searches
@login_required
def search(request):
    """
    Displays all searches made

    **Context**

    ``searchform``
        An search form where the search results can be queried by either their title or the search text used

    ``searches``
        A table displaying all the searches made

    **Template:**

    :template:`parliament/search.html`
    """
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
def search_home(request, sid):
    """
    Displays all models for a given search

    **Context**

    ``search``
        Identification number associated with search object

    ``search_title``
        Title associated with search object

    ``tm_table``
        A table displaying all topic models associated with search object

    ``count``
        Number of occurrences of utterances or paragraphs associated with search object

    ``graph``
        A list of number of utterances or paragraphs associated with search object in each month

    ``s``
        An instance of :model:`parliament.Search`

    ``stat``
        An instance of :model:`tmv_app.RunStats` associated with search

    ``topics``
        All topics associated with ``stat``

    **Template:**

    :template:`parliament/search-home.html`
    """

    template = loader.get_template('parliament/search-home.html')

    # query searches
    s = Search.objects.get(pk=sid)

    tms = RunStats.objects.filter(psearch=s).order_by('-pk')

    tm_table = ModelsTable(tms)

    # count paragraphs/utterances per year

    if s.search_object_type == 1:
        pars = Paragraph.objects.filter(search_matches=s)
        graph = list(pars.filter(utterance__document__date__isnull=False).order_by().annotate(
            year=TruncMonth('utterance__document__date')
        ).order_by('year').values('year').annotate(n = Count('id')))
        count = pars.count()
    else:
        utterances = Utterance.objects.filter(search_matches=s)
        graph = list(utterances.filter(document__date__isnull=False).order_by().annotate(
            year=TruncMonth('document__date')
        ).order_by('year').values('year').annotate(n = Count('id')))
        count = utterances.count()

    for i in range(len(graph)):
        graph[i]['year']=graph[i]['year'].strftime('%Y-%m')

    stat = RunStats.objects.filter(psearch=s).last()
    if stat is None:
        topics = None
    else:
        topics = stat.topic_set.all()

    context = {
        'search': sid,
        'search_title': s.title,
        'tm_table': tm_table,
        'count': count,
        'graph': list(graph),
        's': s,
        'x': 'year',
        'y': 'n',
        'stat': stat,
        'topics': topics
    }

    return HttpResponse(template.render(context, request))


# page for showing topics of a model
@login_required
def model_home(request, model_id):

    template = loader.get_template('parliament/model-home.html')

    stat = RunStats.objects.get(pk=model_id)
    pars = Paragraph.objects.filter(search_matches=stat.psearch)

    graph = list(pars.filter(utterance__document__date__isnull=False).order_by().annotate(
        year=TruncMonth('utterance__document__date')
    ).order_by('year').values('year').annotate(n = Count('id')))

    for i in range(len(graph)):
        graph[i]['year']=graph[i]['year'].strftime('%Y-%m')

    if stat is None:
        topics = None
    else:
        topics = stat.topic_set.all()

    context = {
        'pars': pars,
        'graph': list(graph),
        's': stat.psearch,
        'x': 'year',
        'y': 'n',
        'stat': stat,
        'topics': topics
    }
    return HttpResponse(template.render(context, request))


@login_required
def parl_topic(request, tid, pid=0):
    template = loader.get_template('parliament/parl-topic.html')

    topic = Topic.objects.get(pk=tid)
    stat = topic.run_id
    s = stat.psearch

    if stat.psearch.search_object_type == 1:
        pars = Paragraph.objects.filter(
            search_matches=s,doctopic__topic=topic
        ).order_by(
            '-doctopic__score'
        )

        if pid !=0:
            pars = pars.filter(utterance__speaker__party=Party.objects.get(pk=pid))

        texts_table = SearchParTableTopic(pars)

        texts_table.reg_replace("|".join([s.text] + [x for x in topic.top_words]), stemmer=SnowballStemmer("german").stemmer)
        texts_table.topic_id = tid

        RequestConfig(request).configure(texts_table)

        stat = topic.run_id
        topics = stat.topic_set.all()

        party_totals = Paragraph.objects.filter(
            search_matches=s,
            doctopic__topic__run_id=stat,
            utterance__speaker__party__name__isnull=False,
            utterance__speaker__party__colour__isnull=False
        ).order_by().values('utterance__speaker__party__name').annotate(
            topic_score=Sum(
                Case(
                    When(doctopic__topic=topic, then=F('doctopic__score')),
                    default=0,
                    output_field=models.FloatField()
                )
            ),
            total_score=Sum('doctopic__score'),
        ).annotate(
            topic_proportion=F('topic_score') / F('total_score')
        ).values(
            'topic_proportion',
            'utterance__speaker__party__id',
            'utterance__speaker__party__name',
            'utterance__speaker__party__colour'
        ).order_by('-topic_proportion')

    else:
        uts = Utterance.objects.filter(
            search_matches=s, doctopic__topic=topic
        ).order_by('-doctopic__score')

        if pid !=0:
            uts = uts.filter(speaker__party=Party.objects.get(pk=pid))

        texts_table = SearchSpeechTableTopic(uts)

        texts_table.reg_replace("|".join([s.text]+[x for x in topic.top_words]),stemmer=SnowballStemmer("german").stemmer)
        texts_table.topic_id = tid

        RequestConfig(request).configure(texts_table)

        stat = topic.run_id
        topics = stat.topic_set.all()

        party_totals = Utterance.objects.filter(
            search_matches=s,
            doctopic__topic__run_id=stat,
            speaker__party__name__isnull=False,
            speaker__party__colour__isnull=False
        ).order_by().values('speaker__party__name').annotate(
            topic_score=Sum(
                Case(
                    When(doctopic__topic=topic, then=F('doctopic__score')),
                    default=0,
                    output_field=models.FloatField()
                )
            ),
            total_score=Sum('doctopic__score'),
        ).annotate(
            topic_proportion=F('topic_score') / F('total_score')
        ).values(
            'topic_proportion',
            'speaker__party__id',
            'speaker__party__name',
            'speaker__party__colour'
        ).order_by('-topic_proportion')

    # print(party_totals)

    context = {
        'texts': texts_table,
        's': s,
        'x': 'year',
        'y': 'n',
        'stat': stat,
        'topic': topic,
        'graph': list(party_totals)
    }
    return HttpResponse(template.render(context, request))


@login_required
def person(request,tid):

    template = loader.get_template('parliament/person.html')
    p = Person.objects.get(pk=tid)
    pars = Paragraph.objects.filter(utterance__speaker=p)
    pt = SearchParTable(pars)
    RequestConfig(request).configure(pt)

    seats = SeatTable(
        Seat.objects.filter(occupant=p)
    )


    tweets = tm.Status.objects.filter(author__person=p).order_by('-created_at')[:10]
    # RequestConfig(request).configure(seats)

    context = {
        'p':p,
        'pars': pt,
        'seats': seats,
        'tweets': tweets
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
