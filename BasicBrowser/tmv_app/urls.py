from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

from tmv_app.views import *
from django.contrib.auth.decorators import login_required

app_name = 'tmv_app'

urlpatterns = [
    url(r'^$', login_required(runs), name='index'),
    url(r'^network/(?P<run_id>\d+)$', login_required(network), name='network'),
    url(r'^network_wg/(?P<run_id>\d+)$', login_required(network_wg), name='network_wg'),
    url(r'^return_corrs$', login_required(return_corrs), name='return_corrs'),

    # topic page and topic doc loader
    url(r'^topic/(?P<topic_id>\d+)/$', login_required(topic_detail), name="topic_detail"),
    url(r'^multi_topic/$', login_required(multi_topic), name="multi_topic"),

    url(r'^dynamic_topic/(?P<topic_id>\d+)/$', login_required(dynamic_topic_detail), name="dynamic_topic_detail"),

    url(r'^term/(?P<run_id>\d+)/(?P<term_id>\d+)/$', login_required(term_detail), name="term_detail"),
    url(r'^doc/random/(?P<run_id>\d+)$', login_required(doc_random)),
    url(r'^doc/(?P<doc_id>.+)/(?P<run_id>\d+)$', login_required(doc_detail), name="doc_detail"),
    url(r'^author/(?P<author_name>.+)/(?P<run_id>\d+)$', login_required(author_detail), name="author_detail"),
    url(r'^institution/(?P<run_id>\d+)/(?P<institution_name>.+)/$', login_required(institution_detail)),
    url(r'^topic_list$', login_required(topic_list_detail)),
    # Home page
    url(r'^topic_presence/(?P<run_id>\d+)$', login_required(topic_presence_detail),name="topics"),

    url(r'^topics_time/(?P<run_id>\d+)/(?P<stype>\d+)$', login_required(topics_time),name="topics_time"),

    url(r'^stats/(?P<run_id>\d+)$', login_required(stats)),
    url(r'^settings$', login_required(settings)),
    url(r'^settings/apply$', login_required(apply_settings)),

    url(r'^runs$', login_required(runs), name='runs'),
    url(r'^runs/(?P<pid>\d+)/$', login_required(runs), name='runs'),


    url(r'^queries$', login_required(queries), name='queries'),

    url(r'^adjust_threshold/(?P<run_id>\d+)/$', login_required(adjust_threshold), name='adjust_threshold'),

    url(r'^update/(?P<run_id>\d+)$', login_required(update_run), name='update'),
    url(r'^runs/apply/(?P<new_run_id>\d+)$', login_required(apply_run_filter)),

    url(r'^runs/delete/(?P<new_run_id>\d+)$', login_required(delete_run), name='delete_run'),

    url(r'^topic/random$', login_required(topic_random)),
    url(r'^term/random$', login_required(term_random)),
    url(r'^print_table/(?P<run_id>\d+)$', login_required(print_table), name="print_table"),

    url(r'^compare/(?P<a>\d+)/(?P<z>\d+)$', login_required(compare_runs), name="compare_runs")

    ]


    # Example:
    # (r'^BasicBrowser/', include('BasicBrowser.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),



#onyl serve static content for development
#urlpatterns += static(settings.STATIC_URL,document_root='static')
