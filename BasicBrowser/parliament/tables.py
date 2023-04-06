import django_tables2 as tables
import re
from django_tables2.utils import A
from .models import *
from django.db.models import Q, Count, Func, F, Sum, Value as V
from django.utils.html import format_html
from django.urls import reverse
from .urls import *
from utils.text import *
from tmv_app import models

class ParlTable(tables.Table):
    id = tables.LinkColumn('parliament:parliament', args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    #queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    #tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    class Meta:
        model = Parl
        #fields = ('id','title','description','role','queries','docs','tms')

class ParlPeriodTable(tables.Table):
    docs = tables.LinkColumn('parliament:parlperiod',args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    #queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    #tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    class Meta:
        model = ParlPeriod
        #fields = ('id','title','description','role','queries','docs','tms')

class PersonTable(tables.Table):
    clean_name = tables.LinkColumn(
        'parliament:person',
        args=[A('pk')],
        verbose_name="Full Name"
    )
    contributions = tables.Column()
    words = tables.Column()
    applauded = tables.Column()
    class Meta:
        model=Person
        exclude=(
            'id','short_bio','alt_surnames',
            'alt_first_names','title','ortszusatz',
            'year_of_birth','year_of_death'
        )


class PartyTable(tables.Table):
    name = tables.LinkColumn(
        'parliament:party',
        args=[A('pk')],
    )
    members = tables.Column()
    #contributions = tables.Column()
    class Meta:
        model=Party
        exclude=('id','colour','parliament')


class DocumentTable(tables.Table):
    id = tables.LinkColumn('parliament:document', args=[A('pk')])

    class Meta:
        model = Document
        exclude = ('parlperiod',)


class SearchTable(tables.Table):
    par_count = tables.LinkColumn('parliament:search-list-results',args=[A('pk')])
    id = tables.LinkColumn('parliament:search-home',args=[A('pk')])

    class Meta:
        model = Search


# class to generate model table
class ModelsTable(tables.Table):
    #run_id = tables.LinkColumn('parliament:model-home', args=[A('pk')])
    run_id = tables.LinkColumn('tmv_app:topics', args=[A('pk')])

    class Meta:
        model = models.RunStats
        fields = (
            'run_id','method',
            'start','status',
            'K', 'alpha',
            'top_chain_var',
            'min_freq', 'max_df',
            'rng_seed', 'max_iter',
            'runtime',
            'error','coherence'
            )

class SearchParTable(tables.Table):
    text = tables.Column(verbose_name='Paragraph Text')

    speaker = tables.LinkColumn(
        'parliament:person',args=[A('utterance.speaker.id')],
        accessor='utterance.speaker.clean_name',
        verbose_name='Speaker',
        attrs={'td': {'valign': 'top'}}
    )
    party = tables.LinkColumn(
        'parliament:party',args=[A('utterance.speaker.party.id')],
        accessor='utterance.speaker.party',
        attrs={'td': {'valign': 'top'}}
    )

    utterance = tables.LinkColumn(
        'parliament:utterance', args=[A('utterance.id')],
        accessor='utterance.id',
        verbose_name='From Speech',
        attrs={'td': {'valign':'top'}}
    )

    paragraph_id = tables.LinkColumn(
        'parliament:paragraph', args=[A('id')],
        accessor='id',
        verbose_name='Paragraph ID',
        attrs={'td': {'valign':'top'}}
    )

    document = tables.LinkColumn(
        'parliament:document', args=[A('utterance.document.id')],
        accessor='utterance.document',
        verbose_name='Document',
        attrs={'td': {'valign':'top'}}
    )

    def __init__(self,*args,**kwargs):
        super(SearchParTable, self).__init__(*args, **kwargs)
        self.pattern=None

    def reg_replace(self,pattern,stemmer=None):
        self.pattern = '('+pattern+')'
        self.stemmer=stemmer

    def render_text(self,value):
        if self.pattern is not None:
            parts = re.split(self.pattern,value,flags=re.IGNORECASE)
            parts = value.split()
            if self.stemmer is not None:
                parts_span = ['<span class="h1">'+x+'</span>' if re.match(self.pattern,self.stemmer.stem(x),re.IGNORECASE) else x for x in parts]
            else:
                parts_span = ['<span class="h1">'+x+'</span>' if re.match(self.pattern,x,re.IGNORECASE) else x for x in parts]
            return format_html(' '.join(parts_span))
        else:
            return value

    class Meta:
        model = Paragraph
        exclude = ('id', 'char_len', 'word_count')
        attrs = {'class': 'partable'}


class SearchParTableTopic(SearchParTable):
    score = tables.Column(
        accessor='doctopic_set',
        verbose_name='Score',
        attrs={'td': {'valign': 'top'}}
    )

    def render_score(self, value):
        try:
            score = value.get(topic__id=self.topic_id).score
            score_text = "{0:.3g}".format(score)
        except:
            score_text = ""
        return score_text

    class Meta:
        attrs = {'class': 'partable'}
        sequence = ('paragraph_id', 'utterance', 'speaker', 'party', 'document', 'text', 'score')



# the same as SearchParTable but for utterances
class SearchSpeechTable(tables.Table):

    speech_id = tables.LinkColumn('parliament:utterance',
                             args=[A('id')],
                             accessor='id',
                             verbose_name='Speech ID',
                             attrs={'td': {'valign': 'top'}}
                                  )

    document = tables.LinkColumn('parliament:document',
        args=[A('document.id')],
        accessor='document',
        verbose_name='Document',
        attrs={'td': {'valign':'top'}}
    )

    speaker = tables.LinkColumn(
        'parliament:person',args=[A('speaker.id')],
        accessor='speaker.clean_name',
        verbose_name='Speaker',
        attrs={'td': {'valign': 'top'}}
    )
    party = tables.LinkColumn(
        'parliament:party',args=[A('speaker.party.id')],
        accessor='speaker.party',
        attrs={'td': {'valign': 'top'}}
    )

    text = tables.Column(
        accessor='paragraph_texts',
        verbose_name='Text',
        attrs={'td': {'valign': 'top'}}
    )

    def __init__(self,*args,**kwargs):
        super(SearchSpeechTable, self).__init__(*args, **kwargs)
        self.pattern=None

    def reg_replace(self,pattern,stemmer=None):
        self.pattern = '('+pattern+')'
        self.stemmer=stemmer

    def render_text(self,value):
        if self.pattern is not None:
            parts = re.split(self.pattern,value,flags=re.IGNORECASE)
            parts = value.split()
            if self.stemmer is not None:
                parts_span = ['<span class="h1">'+x+'</span>' if re.match(self.pattern,self.stemmer.stem(x),re.IGNORECASE) else x for x in parts]
            else:
                parts_span = ['<span class="h1">'+x+'</span>' if re.match(self.pattern,x,re.IGNORECASE) else x for x in parts]
            return format_html(' '.join(parts_span))
        else:
            return value


    class Meta:
        model = Utterance
        exclude = ('id','speaker_role')
        attrs = {'class': 'partable'}

class SearchSpeechTableTopic(SearchSpeechTable):
    score = tables.Column(
        accessor='doctopic_set',
        verbose_name='Score',
        attrs={'td': {'valign': 'top'}}
    )

    def render_score(self, value):
        try:
            score = value.get(topic__id=self.topic_id).score
            score_text = "{0:.3g}".format(score)
        except:
            score_text = ""
        return score_text

    class Meta:
        attrs = {'class': 'partable'}
        sequence = ('speech_id', 'speaker', 'party', 'document', 'text', '...')


class SeatTable(tables.Table):

    class Meta:
        model = Seat
        exclude = ('id',)

