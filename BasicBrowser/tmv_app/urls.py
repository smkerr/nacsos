from django.conf.urls import include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from tmv_app.views import *
from django.contrib.auth.decorators import login_required

app_name = 'tmv_app'

urlpatterns = [
    re_path(r'^$', login_required(runs), name='index'),
    path('network/<int:run_id>', login_required(network), name='network'),
    path('network/<int:run_id>/<str:csvtype>', login_required(network), name='network'),
    re_path(r'^network_wg/(?P<run_id>\d+)$', login_required(network_wg), name='network_wg'),
    re_path(r'^network_wg/(?P<run_id>\d+)/(?P<t>\d+)/(?P<f>\d+)/(?P<top>.+)$', login_required(network_wg), name='network_wg'),
    re_path(r'^return_corrs$', login_required(return_corrs), name='return_corrs'),
    re_path(r'^growth/(?P<run_id>\d+)$', login_required(growth_heatmap), name='growth_heatmap'),
    re_path(r'^growth_json/(?P<run_id>\d+)/(?P<v>.+)/$', login_required(growth_json), name='growth_json'),

    # topic page and topic doc loader
    re_path(r'^topic/(?P<topic_id>\d+)/$', login_required(topic_detail), name="topic_detail"),
    re_path(r'^topic/(?P<topic_id>\d+)/(?P<run_id>\d+)/$', login_required(topic_detail), name="topic_detail"),
    re_path(r'^get_topic_docs/(?P<topic_id>\d+)/$', login_required(get_topic_docs), name="get_topic_docs"),
    path('get_topicterms/<int:topic_id>', login_required(get_topicterms), name="get_topicterms"),
    re_path(r'^multi_topic/$', login_required(multi_topic), name="multi_topic"),

    re_path(r'^highlight_dtm_w$', login_required(highlight_dtm_w), name="highlight_dtm_w"),
    re_path(r'^dynamic_topic/(?P<topic_id>\d+)/$', login_required(dynamic_topic_detail), name="dynamic_topic_detail"),

    re_path(r'^term/(?P<run_id>\d+)/(?P<term_id>\d+)/$', login_required(term_detail), name="term_detail"),
    re_path(r'^doc/random/(?P<run_id>\d+)$', login_required(doc_random), name="random_doc"),
    re_path(r'^doc/(?P<doc_id>.+)/(?P<run_id>\d+)$', login_required(doc_detail), name="doc_detail"),
    re_path(r'^author/(?P<author_name>.+)/(?P<run_id>\d+)$', login_required(author_detail), name="author_detail"),
    re_path(r'^institution/(?P<run_id>\d+)/(?P<institution_name>.+)/$', login_required(institution_detail)),
    # Home page
    re_path(r'^topic_presence/(?P<run_id>\d+)$', login_required(topic_presence_detail),name="topics"),

    re_path(r'^topics_time/(?P<run_id>\d+)/(?P<stype>\d+)$', login_required(topics_time),name="topics_time"),
    re_path(r'^topics_time_csv/(?P<run_id>\d+)/$', login_required(get_yt_csv),name="topics_time_csv"),
    re_path(r'^stats/(?P<run_id>\d+)$', login_required(stats), name="stats"),

    re_path(r'^runs$', login_required(runs), name='runs'),
    re_path(r'^runs/(?P<pid>\d+)/$', login_required(runs), name='runs'),

    re_path(r'^adjust_threshold/(?P<run_id>\d+)/(?P<what>.+)$', login_required(adjust_threshold), name='adjust_threshold'),

    re_path(r'^update/(?P<run_id>\d+)$', login_required(update_run), name='update'),
    re_path(r'^runs/delete/(?P<new_run_id>\d+)$', login_required(delete_run), name='delete_run'),

    re_path(r'^topic/random$', login_required(topic_random)),
    re_path(r'^term/random$', login_required(term_random)),
    re_path(r'^print_table/(?P<run_id>\d+)$', login_required(print_table), name="print_table"),

    re_path(r'^compare/(?P<a>\d+)/(?P<z>\d+)$', login_required(compare_runs), name="compare_runs")

    ]


    # Example:
    # (r'^BasicBrowser/', include('BasicBrowser.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),



#onyl serve static content for development
#urlpatterns += static(settings.STATIC_URL,document_root='static')
