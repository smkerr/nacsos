import django_filters
from .models import *

class DocParFilter(django_filters.FilterSet):
    regex = django_filters.CharFilter(
        lookup_expr='regex',
        name="text",
        label="Case sensitive regex"
    )
    iregex = django_filters.CharFilter(
        lookup_expr='iregex',
        name="text",
        label="Case insensitive regex"
    )
    doc_authors = django_filters.CharFilter(
        lookup_expr='icontains',
        name='doc__docauthinst__AU',
        label="Authors include"
    )
    doc_tag = django_filters.NumberFilter(
        lookup_expr='exact',
        name="doc__tag__id",
        label="Document tag"
    )
    class Meta:
        model = DocPar
        fields = {

        }
