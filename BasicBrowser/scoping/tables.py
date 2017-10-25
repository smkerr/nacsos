import django_tables2 as tables
from django_tables2.utils import A
from .models import *

from tmv_app.models import *

#from .urls import urlpatterns


class ProjectTable(tables.Table):
    id = tables.LinkColumn('scoping:project', args=[A('pk')])
    queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    class Meta:
        model = Project
        fields = ('id','title','description','role','queries','docs','tms')


class TopicTable(tables.Table):
    run_id = tables.LinkColumn('tmv_app:topics', args=[A('pk')])
    # queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    # tms = tables.LinkColumn('tmv_app:runs', args=[A('pk')])
    #id = tables.LinkColumn('scoping:project', args=[A('pk')])
    class Meta:
        model = RunStats
        fields = ('run_id','start','status','K')

#from .urls import urlpatterns
