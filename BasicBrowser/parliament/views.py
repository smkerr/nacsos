from django.shortcuts import render
from django.template import loader, RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django_tables2.config import RequestConfig
from parliament.models import *
from .tables import *
from .forms import *
from .tasks import *
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

@login_required
def parliament(request,pid):

    template = loader.get_template('parliament/parliament.html')

    parl = Parl.objects.get(pk=pid)
    ps  = ParlSession.objects.filter(parliament=parl).annotate(
        docs = Count('document')
    )
    ps = ParlSessionTable(ps, order_by="id")

    persons = Person.objects.filter(
        utterance__document__parlsession__parliament=parl
    ).annotate(
        contributions=Count('utterance')
    )

    persons = PersonTable(persons)#.paginate()
    persons.paginate(page=request.GET.get('page',1),per_page=25)
    RequestConfig(request).configure(persons)


    context = {
        'ps': ps,
        'parl': parl,
        'persons': persons
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
        )
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
    pt = SearchParTable(pars,"bla")
    pt.reg_replace(s.text)
    RequestConfig(request).configure(pt)

    context = {
        'pars': pt,
    }

    return HttpResponse(template.render(context, request))
