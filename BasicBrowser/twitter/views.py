from rest_framework import viewsets
import django_filters.rest_framework
from twitter.models import *
from twitter.filters import *
from twitter.serializers import *

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('created_at')
    serializer_class = UserSerializer
    filter_class = UserFilter

class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Status.objects.all().order_by('created_at')
    serializer_class = StatusSerializer
    filter_class = StatusFilter
    #filter_fields = ('text', )
    #filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)

class TwitterSearchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TwitterSearch.objects.all()
    serializer_class = TwitterSearchSerializer
