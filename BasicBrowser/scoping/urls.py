from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from scoping import views

app_name = 'scoping'

urlpatterns = [


    # Homepage, projet management

    url(r'^$', views.index, name='index'),
    url(r'^project/(?P<pid>[0-9]+)/$', views.project, name='project'),



    # Query management


    #### Index pages / query set-up (user input)


    url(r'^queries/(?P<pid>[0-9]+)/$', views.queries, name='queries'),
    url(r'^query_table/(?P<pid>[0-9]+)/$', views.query_table, name='query_table'),


    url(r'^docs/(?P<pid>[0-9]+)/(?P<qid>[0-9]+)$', views.doclist, name='doclist'),

    url(r'^doquery/(?P<pid>[0-9]+)$', views.doquery, name='doquery'),


    url(r'^snowball$', views.snowball, name='snowball'),
    #### Query processing
    url(r'^start_snowballing$', views.start_snowballing, name='start_snowballing'),
    url(r'^doquery$', views.doquery, name='doquery'),
    url(r'^do_snowballing/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)$', views.do_snowballing, name='do_snowballing'),
    url(r'^dodocadd/(?P<qid>[0-9]+)$', views.dodocadd, name='dodocadd'),
    url(r'^querying/(?P<qid>[0-9]+)/(?P<substep>[0-9]+)/(?P<docadded>[0-9]+)/(?P<q2id>[0-9]+)$', views.querying, name='querying'),
    url(r'^querying/(?P<qid>[0-9]+)/(?P<substep>[0-9]+)/(?P<docadded>[0-9]+)/$', views.querying, name='querying'),
    url(r'^querying/(?P<qid>[0-9]+)/$', views.querying, name='querying'),
    url(r'^snowball_progress/(?P<sbs>[0-9]+)/$', views.snowball_progress, name='snowball_progress'),

    #### Manage Query
    url(r'^query/(?P<qid>[0-9]+)/$', views.query, name='query'),

    #### Manage SBS
    url(r'^sbs_allocateDocsToUser/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)$', views.sbs_allocateDocsToUser, name='sbs_allocateDocsToUser'),
    url(r'^sbs_setAllQDocsToIrrelevant/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<sbsid>[0-9]+)$', views.sbs_setAllQDocsToIrrelevant, name='sbs_setAllQDocsToIrrelevant'),
    url(r'^sbsKeepDoc/(?P<qid>[0-9]+)/(?P<did>.+)$', views.sbsKeepDoc, name='sbsKeepDoc'),
    url(r'^sbsExcludeDoc/(?P<qid>[0-9]+)/(?P<did>.+)$', views.sbsExcludeDoc, name='sbsExcludeDoc'),
    url(r'^delete_query/(?P<qid>[0-9]+)$', views.delete_query, name='delete'),
    url(r'^delete_sbs/(?P<sbsid>[0-9]+)$', views.delete_sbs, name='delete'),

    #### Others
    ## Cities
    url(r'^cities/(?P<qid>[0-9]+)$',views.cities, name='cities'),
    url(r'^city_data/(?P<qid>[0-9]+)$',views.city_data, name='city_data'),
    url(r'^city_docs/(?P<qid>[0-9]+)$',views.city_docs, name='city_docs'),

    url(r'^switchmode$', views.switch_mode, name='switch_mode'),

    url(r'^technologies/(?P<pid>[0-9]+)',views.technologies, name='technologies'),
    url(r'^technology/(?P<tid>[0-9]+)$',views.technology, name='technology'),
    url(r'^download_tdocs/(?P<tid>[0-9]+)$',views.download_tdocs, name='download_tdocs'),
    url(r'^authorlist/(?P<tid>[0-9]+)$',views.prepare_authorlist, name='authorlist'),
    url(r'^sendauthorlist/(?P<tid>[0-9]+)$',views.send_authorlist, name='send_authorlist'),

    url(r'^add_tech',views.add_tech, name='add_tech'),
    url(r'^update_tech',views.update_tech, name='update_tech'),

    url(r'^user/(?P<pid>[0-9]+)$', views.userpage, name='userpage'),

    url(r'^update_criteria$', views.update_criteria, name='update_criteria'),

    url(r'^docs/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<sbsid>[0-9]+)$', views.doclist, name='doclistsbs'),

    url(r'^docssbs/(?P<sbsid>[0-9]+)$', views.doclistsbs, name='doclistsbs'),
    url(r'^docrellist/(?P<sbsid>[0-9]+)/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<q3id>[0-9]+)$', views.docrellist, name='docrellist'),
    url(r'^sort_docs$', views.sortdocs, name='sortdocs'),
    url(r'^cycle_score$', views.cycle_score, name='cycle_score'),
    url(r'^activate_user$', views.activate_user, name='activate_user'),
    url(r'^assign_docs$', views.assign_docs, name='assign_docs'),
    url(r'^remove_assignments$', views.remove_assignments, name='remove_assignments'),
    #### Individual docs
    url(r'^screen/(?P<qid>[0-9]+)/(?P<tid>[0-9]+)/(?P<ctype>[0-9]+)/(?P<d>[-0-9]+)$', views.screen, name='screen'),
    url(r'^do_review$', views.do_review, name='do_review'),
    url(r'^add_note', views.add_note, name='add_note'),

    # Nice function for updateing many things
    url(r'^update_thing',views.update_thing, name='update_thing'),


    url(r'^download/(?P<qid>[0-9]+)', views.download, name='download'),
    url(r'^delete/(?P<thing>[a-zA-Z]+)/(?P<thingid>[0-9]+)$', views.delete, name='delete'),
    url(r'^manual_add/(?P<pid>[0-9]+)$', views.add_doc_form, name='manual_add_doc_form'),

    url(r'^external_add/(?P<authtoken>[0-9a-f-]+)$', views.add_doc_form, name='add_doc_form'),
    url(r'^external_add/(?P<authtoken>[0-9a-f-]+)/(?P<r>[0-9]+)$', views.add_doc_form, name='add_doc_form'),
    url(r'^do_add_doc/$', views.do_add_doc, name='do_add_doc'),
    url(r'^do_add_doc/(?P<authtoken>[0-9a-f-]+)$', views.do_add_doc, name='do_add_doc'),
    url(r'^editdoc$', views.editdoc, name='editdoc'),
    url(r'^document/(?P<pid>.+)/(?P<doc_id>.+)/$', views.document, name='document'),
    url(r'^remove_tech/(?P<doc_id>.+)/(?P<tid>[0-9]+)/(?P<thing>.+)$', views.remove_tech, name='remove_tech'),

]
