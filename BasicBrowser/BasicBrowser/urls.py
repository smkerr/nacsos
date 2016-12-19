from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    url(r'^tmv_app/', include('tmv_app.urls')),
    url(r'^scoping/', include('scoping.urls')),
    url(r'^admin/', admin.site.urls),
 	url(r'^accounts/login/$', auth_views.login, {'template_name': 'admin/login.html'}),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
