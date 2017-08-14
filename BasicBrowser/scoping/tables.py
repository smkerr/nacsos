import django_tables2 as tables
from .models import *

class ProjectTable(tables.Table):
    class Meta:
        model = Project
        fields = ('id','title','description','owner','queries','docs')
