import django_tables2 as tables
import re
from django_tables2.utils import A
from .models import *
from django.db.models import Q, Count, Func, F, Sum, Value as V
from django.utils.html import format_html
from django.urls import reverse
from .urls import *

class ParlTable(tables.Table):
    id = tables.LinkColumn('parliament:parliament', args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    #queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    #tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    class Meta:
        model = Parl
        #fields = ('id','title','description','role','queries','docs','tms')

class ParlSessionTable(tables.Table):
    docs = tables.LinkColumn('parliament:psession',args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    #queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    #tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    class Meta:
        model = ParlSession
        #fields = ('id','title','description','role','queries','docs','tms')

class PersonTable(tables.Table):
    contributions = tables.Column()
    class Meta:
        model=Person


class DocumentTable(tables.Table):
    id = tables.LinkColumn('parliament:document', args=[A('pk')])
    class Meta:
        model = Document
        exclude = ('parlsession')


class SearchTable(tables.Table):
    par_count = tables.LinkColumn('parliament:search-pars',args=[A('pk')])

    class Meta:
        model = Search


class SearchParTable(tables.Table):
    text = tables.Column()
    speaker = tables.Column(
        accessor='utterance.speaker.clean_name',verbose_name='Speaker'
    )
    utterance = tables.Column(
        accessor='utterance',
        verbose_name='Document'
    )
    def __init__(self,*args,**kwargs):
        super(SearchParTable, self).__init__(*args, **kwargs)

    def render_utterance(self,value):
        d = value.document
        l = reverse("parliament:document",args=[d.pk])+'#utterance_'+str(value.id)
        t = "{} - {} , {}".format(d.date, d.doc_type,d.parlsession.n)
        return format_html('<a href="{}">{}</a>'.format(l,t))

    def reg_replace(self,pattern):
        self.pattern = '('+pattern+')'

    def render_text(self,value):
        parts = re.split(self.pattern,value,flags=re.IGNORECASE)
        parts_span = ['<span class="h1">'+x+'</span>' if re.match(self.pattern,x,re.IGNORECASE) else x for x in parts]
        return format_html(''.join(parts_span))

    class Meta:
        model = Paragraph
        exclude = ('id',)
