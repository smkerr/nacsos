from django.contrib.auth.decorators import login_required
from scoping import views
from django.urls import path, re_path

app_name = 'scoping'

urlpatterns = [


    # Homepage, projet management

    re_path(r'^$', views.index, name='index'),
    re_path(r'^project/(?P<pid>[0-9]+)/$', views.project, name='project'),



    # Query management


    #### Index pages / query set-up (user input)


    re_path(r'^queries/(?P<pid>[0-9]+)/$', views.queries, name='queries'),
    re_path(r'^query_table/(?P<pid>[0-9]+)/$', views.query_table, name='query_table'),

    path('generate_query/<int:pid>/<int:t>', views.generate_query,name="generate_query"),


    re_path(r'^docs/(?P<pid>[0-9]+)/(?P<qid>[0-9]+)$', views.doclist, name='doclist'),

    re_path(r'^create_query/(?P<pid>[0-9]+)$', views.create_query, name='create_query'),

    path('project/<int:pid>/query/add/', login_required(views.QueryCreate.as_view()),name="query_create"),
    path('duplicates/<int:pid>', views.manage_duplicates, name="manage_duplicates"),


    path('find_duplicates/<int:pid>', views.find_duplicates, name="find_duplicates"),
    path('doc_info/<int:did>/<int:did2>', views.doc_info, name="doc_info"),
    path('doc_merge/<int:pid>/<int:d1>/<int:d2>', views.doc_merge, name="doc_merge"),

    ### Paragraph stuff
    path('paragraphs/<int:qid>', views.par_manager, name="par_manager"),

    path('screen_par/<int:tid>/<int:ctype>/<int:doid>/<int:todo>/<int:done>/<int:last_doid>', views.screen_par, name="screen_par"),
    path('add_statement', views.add_statement, name="add_statement"),
    path('del_statement', views.del_statement, name="del_statement"),
    path('rate_par/<int:tid>/<int:ctype>/<int:doid>/<int:todo>/<int:done>', views.rate_par, name="rate_par"),

    ### twitter
    path('twitter-home/<int:pid>', views.twitter_home, name="twitter_home"),
    path('twitter-home/download_screened_tweets/<int:pid>', views.download_screened_tweets, name="download_screened_tweets"),


    ### Meta-analysis stuff
    path('meta-setup/<int:pid>', views.meta_setup, name="meta_setup"),
    path('meta-setup/assign_meta', views.assign_meta, name="assign_meta"),
    path('meta-setup/download_effects/<int:pid>', views.download_effects, name="download_effects"),
    path('meta-setup/report/<int:pid>', views.meta_report, name="meta_report"),
    path('code-document/<int:docmetaid>',views.code_document,name='code_document'),
    path('code-document/<int:docmetaid>/<int:reorder>',views.code_document,name='code_document'),
    path('exclude-document/<int:dmc>',views.ExcludeView.as_view(), name="exclude"),
    path('save-document-code/<int:docmetaid>/<int:dest>',views.save_document_code,name='save_document_code'),
    path('add-effect/<int:docmetaid>',views.add_effect,name='add_effect'),
    path('add-effect/<int:docmetaid>/<int:eff_copy>',views.add_effect,name='add_effect'),
    path('add-effect/<int:docmetaid>/<int:eff_copy>/<int:eff_edit>',views.add_effect,name='add_effect'),
    path('add-intervention/<int:effectid>',views.add_intervention,name='add_intervention'),
    path('add-intervention/<int:effectid>/<int:iid>',views.add_intervention,name='add_intervention'),
    path('add-intervention/<int:effectid>/<int:iid>/<int:i_edit>',views.add_intervention,name='add_intervention'),
    path('download-calculations/<int:id>', views.download_calculations, name="download_calculations"),


    path('db1-db2-report/<int:tagid>', views.db1_db2_report, name="db1_db2_report"),
    path('tag-comparison/<int:tagid>', views.tag_comparison, name="tag_comparison"),

    path('risk-of-bias/<int:dmcid>', login_required(views.RoBCreate.as_view()),name="rob_create"),
    path('edit-risk-of-bias/<int:dmcid>', login_required(views.RoBEdit.as_view()),name="rob_edit"),

    re_path(r'^snowball$', views.snowball, name='snowball'),
    #### Query processing
    re_path(r'^start_snowballing$', views.start_snowballing, name='start_snowballing'),
    re_path(r'^do_snowballing/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)$', views.do_snowballing, name='do_snowballing'),
    re_path(r'^dodocadd/(?P<qid>[0-9]+)$', views.dodocadd, name='dodocadd'),
    re_path(r'^querying/(?P<qid>[0-9]+)/(?P<substep>[0-9]+)/(?P<docadded>[0-9]+)/(?P<q2id>[0-9]+)$', views.querying, name='querying'),
    re_path(r'^querying/(?P<qid>[0-9]+)/(?P<substep>[0-9]+)/(?P<docadded>[0-9]+)/$', views.querying, name='querying'),
    re_path(r'^querying/(?P<qid>[0-9]+)/$', views.querying, name='querying'),
    re_path(r'^snowball_progress/(?P<sbs>[0-9]+)/$', views.snowball_progress, name='snowball_progress'),

    #### Manage Query
    re_path(r'^query/(?P<qid>[0-9]+)/$', views.query, name='query'),
    path('query_dev/<int:qid>/', views.query_dev, name='query_dev'),
    re_path(r'^query-tm-manager/(?P<qid>[0-9]+)/$', views.query_tm_manager, name='query_tm_manager'),
    re_path(r'^query-tm/(?P<qid>[0-9]+)/$', views.query_tm, name='query_tm'),
    re_path(r'^run_model-tm/(?P<run_id>[0-9]+)/$', views.run_model, name='run_model'),

    ### Topic model checking
    path('word_intrusion/<int:run_id>', views.word_intrusion, name="word_intrusion"),
    path('proc_word_intrusion/<int:wid>/<int:tid>', views.proc_word_intrusion, name="proc_word_intrusion"),

    path('topic_intrusion/<int:run_id>', views.topic_intrusion, name="topic_intrusion"),
    path('proc_topic_intrusion/<int:tid>/<int:top_id>', views.proc_topic_intrusion, name="proc_topic_intrusion"),

    #### Manage SBS
    re_path(r'^sbs_allocateDocsToUser/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)$', views.sbs_allocateDocsToUser, name='sbs_allocateDocsToUser'),
    re_path(r'^sbs_setAllQDocsToIrrelevant/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<sbsid>[0-9]+)$', views.sbs_setAllQDocsToIrrelevant, name='sbs_setAllQDocsToIrrelevant'),
    re_path(r'^sbsKeepDoc/(?P<qid>[0-9]+)/(?P<did>.+)$', views.sbsKeepDoc, name='sbsKeepDoc'),
    re_path(r'^sbsExcludeDoc/(?P<qid>[0-9]+)/(?P<did>.+)$', views.sbsExcludeDoc, name='sbsExcludeDoc'),
    re_path(r'^delete_query/(?P<qid>[0-9]+)$', views.delete_query, name='delete'),
    re_path(r'^delete_sbs/(?P<sbsid>[0-9]+)$', views.delete_sbs, name='delete'),

    #### Others
    ## Cities
    re_path(r'^cities/(?P<qid>[0-9]+)$',views.cities, name='cities'),
    re_path(r'^city_data/(?P<qid>[0-9]+)$',views.city_data, name='city_data'),
    re_path(r'^city_docs/(?P<qid>[0-9]+)$',views.city_docs, name='city_docs'),

    re_path(r'^switchmode$', views.switch_mode, name='switch_mode'),

    re_path(r'^categories/(?P<pid>[0-9]+)',views.categories, name='categories'),
    path('filter_categories/<int:pid>/<int:level>', views.filter_categories, name="filter_categories"),
    re_path(r'^category/(?P<tid>[0-9]+)$',views.category, name='category'),
    re_path(r'^download_tdocs/(?P<tid>[0-9]+)$',views.download_tdocs, name='download_tdocs'),
    re_path(r'^authorlist/(?P<tid>[0-9]+)$',views.prepare_authorlist, name='authorlist'),
    re_path(r'^sendauthorlist/(?P<tid>[0-9]+)$',views.send_authorlist, name='send_authorlist'),

    re_path(r'^textplace-autocomplete/$',views.TextPlaceAutocomplete.as_view(create_field='name'),name="textplace-autocomplete"),
    path(r'textfree-autocomplete/',views.TextFreeAutocomplete.as_view(create_field='name'),name="textfree-autocomplete"),
    re_path(r'^country-autocomplete/$',views.CountryAutocomplete.as_view(create_field='name'),name="country-autocomplete"),

    path('duc_country', views.duc_country, name='duc_country'),
    path('duc_place', views.duc_place, name='duc_place'),
    path('duc_text', views.duc_text, name='duc_text'),
    path('duc_year', views.duc_year, name='duc_year'),
    path('duc_number', views.duc_number, name='duc_number'),

    re_path(r'^add_othercat',views.add_othercat, name='add_othercat'),
    re_path(r'^del_othercat',views.del_othercat, name='del_othercat'),

    re_path(r'^add_tech',views.add_tech, name='add_tech'),
    re_path(r'^async_add_tech',views.async_add_tech, name='async_add_tech'),
    path('update_tech/<int:tid>',views.update_tech, name='update_tech'),

    re_path(r'^user/(?P<pid>[0-9]+)$', views.userpage, name='userpage'),

    re_path(r'^update_criteria$', views.update_criteria, name='update_criteria'),

    re_path(r'^docs/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<sbsid>[0-9]+)$', views.doclist, name='doclistsbs'),

    re_path(r'^docssbs/(?P<sbsid>[0-9]+)$', views.doclistsbs, name='doclistsbs'),
    re_path(r'^docrellist/(?P<sbsid>[0-9]+)/(?P<qid>[0-9]+)/(?P<q2id>[0-9]+)/(?P<q3id>[0-9]+)$', views.docrellist, name='docrellist'),
    re_path(r'^sort_docs$', views.sortdocs, name='sortdocs'),
    path('export-docs/<int:qid>/',views.export_ris_docs,name='export-docs'),

    re_path(r'^cycle_score$', views.cycle_score, name='cycle_score'),
    re_path(r'^activate_user$', views.activate_user, name='activate_user'),
    re_path(r'^assign_docs$', views.assign_docs, name='assign_docs'),
    re_path(r'^remove_assignments$', views.remove_assignments, name='remove_assignments'),


    #### Individual docs
    re_path(r'^screen/(?P<tid>[0-9]+)/(?P<ctype>[0-9]+)/(?P<d>[-0-9]+)$', views.screen, name='screen'),
    re_path(r'^do_review$', views.do_review, name='do_review'),
    re_path(r'^add_note', views.add_note, name='add_note'),

    path('screen_doc/<int:doid>', views.screen_doc_id, name='screen_doc_id'),
    path('screen_doc/<int:tid>/<int:ctype>/<int:pos>/<int:todo>', views.screen_doc, name='screen_doc'),
    path('screen_doc/<int:tid>/<int:ctype>/<int:pos>/<int:todo>/<int:js>', views.screen_doc, name='screen_doc'),

    path('rate_doc/<int:tid>/<int:ctype>/<int:doid>/<int:pos>/<int:todo>/<int:rel>', views.rate_doc, name='rate_doc'),
    path('cat_doc/', views.cat_doc, name='cat_doc'),

    # Nice function for updateing many things
    re_path(r'^update_thing',views.update_thing, name='update_thing'),


    re_path(r'^download/(?P<qid>[0-9]+)', views.download, name='download'),
    re_path(r'^download_pdf/(?P<id>[0-9]+)', views.download_pdf, name='download_pdf'),
    re_path(r'^delete/(?P<thing>[a-zA-Z]+)/(?P<thingid>[0-9]+)$', views.delete, name='delete'),
    re_path(r'^manual_add/(?P<pid>[0-9]+)$', views.create_internal_et, name='manual_add_doc_form'),

    re_path(r'^external_add/(?P<authtoken>[0-9a-f-]+)$', views.add_doc_form, name='add_doc_form'),
    re_path(r'^external_add/(?P<authtoken>[0-9a-f-]+)/(?P<did>[0-9]+)$', views.add_doc_form, name='add_doc_form'),
    #re_path(r'^external_add/(?P<authtoken>[0-9a-f-]+)/(?P<r>[0-9]+)$', views.add_doc_form, name='add_doc_form'),
    re_path(r'^editdoc$', views.editdoc, name='editdoc'),
    re_path(r'^document/(?P<pid>.+)/(?P<doc_id>.+)/$', views.document, name='document'),
    re_path(r'^remove_tech/(?P<doc_id>.+)/(?P<tid>[0-9]+)/(?P<thing>.+)$', views.remove_tech, name='remove_tech'),

]
