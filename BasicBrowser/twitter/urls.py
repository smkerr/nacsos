from django.urls import include, path
from rest_framework import routers

import twitter.views

router = routers.DefaultRouter()
router.register(r'users', twitter.views.UserViewSet)
router.register(r'statuses', twitter.views.StatusViewSet)
router.register(r'searches', twitter.views.TwitterSearchViewSet)

urlpatterns = [
    path('api_auth/', include('rest_framework.urls')),
    path('', include(router.urls)),
]
