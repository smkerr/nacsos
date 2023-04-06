from django.conf.urls import include
from django.contrib import admin
from django.conf import settings
from django.contrib.auth import views as auth_views
from scoping import views
import BasicBrowser.views as site_views
from django.urls import include, path
from django.views.defaults import page_not_found
from django.conf import settings
from django.urls import re_path
import scoping

# handler404 = scoping.views.handler404


if settings.MAINTENANCE:
    urlpatterns = [
        re_path(r'^', scoping.views.handler404, name="maintenance"),
    ]
else:
    urlpatterns = [
        path('nacsos-legacy/', include([
            # path('lotto/', include('lotto.urls')),
            path('admin/doc/', include('django.contrib.admindocs.urls')),
            # re_path(r'^', scoping.views.handler404, name="maintenance"),
            # path('404', page_not_found, {'exception': Exception()}),
            re_path(r'^tmv_app/', include('tmv_app.urls')),
            re_path(r'^scoping/', include('scoping.urls')),
            re_path(r'^parliament/', include('parliament.urls')),
            path('twitter/', include('twitter.urls')),
            path('lotto', include('lotto.urls')),
            path('signup', site_views.signup, name='signup'),
            re_path(r'^admin/', admin.site.urls),
            re_path(r'^$', site_views.index),
            # path('accounts/', include('django.contrib.auth.urls')),
            path('accounts/password_reset', auth_views.PasswordResetView.as_view(success_url="/"),
                 name="password_reset"),
            path('accounts/password_change', auth_views.PasswordChangeView.as_view(success_url="/scoping"),
                 name="password_change"),
            path('accounts/login/', auth_views.LoginView.as_view(success_url="/"),
                 {'template_name': 'scoping/login.html'}),
            re_path(r'^accounts/logout/$', views.logout_view, name='logout_view'),
        ]))
    ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
