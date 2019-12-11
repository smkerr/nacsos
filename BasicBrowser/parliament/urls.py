from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from parliament import views

app_name = 'parliament'

urlpatterns = [

    # Homepage, Parliaments
    url(r'^$', views.index, name='index'),

    #Parliament pages
    url(r'^parliament/(?P<pid>[0-9]+)/$', views.parliament, name='parliament'),
    url(r'^parties/(?P<pid>[0-9]+)/$', views.parties, name='parties'),
    url(r'^persons/(?P<pid>[0-9]+)/$', views.persons, name='persons'),

    url(r'^session/(?P<pid>[0-9]+)/$', views.parlperiod, name='parlperiod'),

    url(r'^search/$', views.search, name='search'),
    url(r'^search-home/(?P<sid>[0-9]+)/$', views.search_home, name='search-home'),
    url(r'^search-list-results/(?P<sid>[0-9]+)/$', views.search_list_results, name='search-list-results'),

    url(r'^model-home/(?P<model_id>[0-9]+)/$', views.model_home, name='model-home'),

    url(r'^parl-topic/(?P<tid>[0-9]+)/$', views.parl_topic, name='parl-topic'),
    url(r'^parl-topic/(?P<tid>[0-9]+)/(?P<pid>[0-9]+)$', views.parl_topic, name='parl-topic-party'),

    url(r'^person/(?P<tid>[0-9]+)/$', views.person, name='person'),
    url(r'^party/(?P<tid>[0-9]+)/$', views.party, name='party'),

    url(r'^document/(?P<did>[0-9]+)/$', views.document, name='document'),
    url(r'^utterance/(?P<ut_id>[0-9]+)/$', views.utterance, name='utterance'),
    url(r'^paragraph/(?P<par_id>[0-9]+)/$', views.paragraph, name='paragraph'),

]
