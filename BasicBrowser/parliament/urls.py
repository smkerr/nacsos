from django.contrib.auth.decorators import login_required
from parliament import views
from django.urls import re_path
app_name = 'parliament'

urlpatterns = [

    # Homepage, Parliaments
    re_path(r'^$', views.index, name='index'),

    #Parliament pages
    re_path(r'^parliament/(?P<pid>[0-9]+)/$', views.parliament, name='parliament'),
    re_path(r'^parties/(?P<pid>[0-9]+)/$', views.parties, name='parties'),
    re_path(r'^persons/(?P<pid>[0-9]+)/$', views.persons, name='persons'),

    re_path(r'^session/(?P<pid>[0-9]+)/$', views.parlperiod, name='parlperiod'),

    re_path(r'^search/$', views.search, name='search'),
    re_path(r'^search-home/(?P<sid>[0-9]+)/$', views.search_home, name='search-home'),
    re_path(r'^search-list-results/(?P<sid>[0-9]+)/$', views.search_list_results, name='search-list-results'),

    re_path(r'^model-home/(?P<model_id>[0-9]+)/$', views.model_home, name='model-home'),

    re_path(r'^parl-topic/(?P<tid>[0-9]+)/$', views.parl_topic, name='parl-topic'),
    re_path(r'^parl-topic/(?P<tid>[0-9]+)/(?P<pid>[0-9]+)$', views.parl_topic, name='parl-topic-party'),

    re_path(r'^person/(?P<tid>[0-9]+)/$', views.person, name='person'),
    re_path(r'^party/(?P<tid>[0-9]+)/$', views.party, name='party'),

    re_path(r'^document/(?P<did>[0-9]+)/$', views.document, name='document'),
    re_path(r'^utterance/(?P<ut_id>[0-9]+)/$', views.utterance, name='utterance'),
    re_path(r'^paragraph/(?P<par_id>[0-9]+)/$', views.paragraph, name='paragraph'),

]
