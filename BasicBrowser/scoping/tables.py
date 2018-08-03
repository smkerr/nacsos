import django_tables2 as tables
from django_tables2.utils import A
from .models import *
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from tmv_app.models import *
from .filters import *
import django_filters

#from .urls import urlpatterns

class DocTable(tables.Table):
    class Meta:
        model = Doc


class ProjectTable(tables.Table):
    id = tables.LinkColumn('scoping:project', args=[A('pk')])
    queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    role = tables.Column()
    class Meta:
        model = Project
        fields = ('id','title','description','queries','docs','tms')
        template_name = 'django_tables2/bootstrap.html'
        attrs = {'class': 'table'}

class FloatColumn(tables.Column):
    # def __init__(self, **kwargs):
    #     if 'digits' in kwargs:
    #         self.digits = kwargs['digits']
    #     else:
    #         self.digits = 2
    def render(self, value):
        return round(value,3)

class TopicTable(tables.Table):
    run_id = tables.LinkColumn('tmv_app:topics', args=[A('pk')])
    error = FloatColumn()
    coherence = FloatColumn()
    # queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    # tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    # startit = tables.LinkColumn(
    #     'scoping:run_model',
    #     text='Start',
    #     args=[A('pk')]
    # )
    class Meta:
        model = RunStats
        fields = (
            'run_id','method',
            'start','status',
            'K','alpha',
            'min_freq','max_df',
            'error','coherence',
            'psearch'
        )#'startit')

#from .urls import urlpatterns

class DocParTable(tables.Table):

    document = tables.Column(
        accessor='doc.title',
        verbose_name='Document'
    )
    authors = tables.Column(
        accessor='doc.authors',
        verbose_name='Authors'
    )
    py = tables.Column(
        accessor='doc.PY',
        verbose_name='Publication Year'
    )
    file = tables.LinkColumn(
        'scoping:download_pdf',args=[A('doc.docfile.id')],
        accessor='doc.docfile.file',
        verbose_name="File"
    )


    class Meta:
        model = DocPar
        fields = (
            'document','authors','py','text','n'
        )
        template_name = 'django_tables2/bootstrap.html'
        attrs = {'class': 'table'}


class FilteredDocPar(SingleTableMixin, FilterView):
    table_class = DocParTable
    model = DocPar
    template_name = 'par_manager.html'

    filterset_class = DocParFilter

class TagTable(tables.Table):
    class Meta:
        model = Tag
        fields = (
            'title',
        )
