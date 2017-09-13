import django_tables2 as tables
from django_tables2.utils import A
from .models import *
#from .urls import urlpatterns




class ProjectTable(tables.Table):
    id = tables.LinkColumn('scoping:project', args=[A('pk')])
    queries = tables.LinkColumn('scoping:queries', args=[A('pk')])
    class Meta:
        model = Project
        fields = ('id','title','description','role','queries','docs')
