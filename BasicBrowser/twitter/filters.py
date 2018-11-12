import django_filters

from twitter.models import *

class StatusFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = Status
        fields = {
            'text': ['icontains'],
            'author__screen_name': ['exact'],
            'retweeted_by__screen_name': ['exact']
        }

class UserFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = User
        fields = {
            'screen_name': ['iexact'],
        }
