from django.conf.urls import url

from . import views

app_name = 'scoping'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^doquery$', views.doquery, name='doquery'),
    url(r'^querying/(?P<qid>[0-9]+)$', views.querying, name='querying'),
    url(r'^docs/(?P<qid>[0-9]+)$', views.doclist, name='doclist'),
    url(r'^sort_docs$', views.sortdocs, name='sortdocs'),
]
