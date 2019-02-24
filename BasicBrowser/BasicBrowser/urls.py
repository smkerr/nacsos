from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.contrib.auth import views as auth_views
from scoping import views
import BasicBrowser.views as site_views
from django.urls import include, path
from django.views.defaults import page_not_found
from django.conf import settings

import scoping

handler404 = scoping.views.handler404

x = settings.DEBUG
y = dir(settings)

if settings.MAINTENANCE:
    urlpatterns = [
        url(r'^', scoping.views.handler404, name="maintenance"),
    ]
else:
    urlpatterns = [
        #path('lotto/', include('lotto.urls')),
        path('admin/doc/', include('django.contrib.admindocs.urls')),
        #url(r'^', scoping.views.handler404, name="maintenance"),
        #path('404', page_not_found, {'exception': Exception()}),
        url(r'^tmv_app/', include('tmv_app.urls')),
        url(r'^scoping/', include('scoping.urls')),
        url(r'^parliament/', include('parliament.urls')),
        path('twitter/', include('twitter.urls')),
        path('lotto', include('lotto.urls')),
        url(r'^admin/', admin.site.urls),
        url(r'^$', site_views.index),
        path('accounts/password_change', auth_views.PasswordChangeView.as_view(success_url="/scoping"), name="password_change"),
        path('accounts/login/', auth_views.LoginView.as_view(), {'template_name': 'scoping/login.html'}),
        url(r'^accounts/logout/$', views.logout_view, name='logout_view'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
