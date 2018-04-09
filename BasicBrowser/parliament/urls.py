from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from parliament import views

app_name = 'parliament'

urlpatterns = [

    # Homepage, Parliaments
    url(r'^$', views.index, name='index'),

    #Parliament page
    url(r'^parliament/(?P<pid>[0-9]+)/$', views.parliament, name='parliament'),
    url(r'^session/(?P<pid>[0-9]+)/$', views.psession, name='psession'),

    url(r'^search/$', views.search, name='search'),
    url(r'^search-home/(?P<sid>[0-9]+)/$', views.search_home, name='search-home'),
    url(r'^search-pars/(?P<sid>[0-9]+)/$', views.search_pars, name='search-pars'),

    url(r'^parl-topic/(?P<tid>[0-9]+)/$', views.parl_topic, name='parl-topic'),
    url(r'^parl-topic/(?P<tid>[0-9]+)/(?P<pid>[0-9]+)$', views.parl_topic, name='parl-topic-party'),

    url(r'^person/(?P<tid>[0-9]+)/$', views.person, name='person'),
    url(r'^party/(?P<tid>[0-9]+)/$', views.party, name='party'),

    url(r'^document/(?P<did>[0-9]+)/$', views.document, name='document'),

]
