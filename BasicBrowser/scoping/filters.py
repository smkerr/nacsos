import django_filters
from .models import *

class DocParFilter(django_filters.FilterSet):
    class Meta:
        model = DocPar
        fields = {
            #'document',
            'text': ['icontains','iregex'],
        }
