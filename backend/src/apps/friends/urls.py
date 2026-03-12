from django.urls import include, path
from rest_framework.routers import DefaultRouter

from src.apps.friends.views import FriendRequestViewSet, FriendViewSet

router = DefaultRouter()
router.register(r"requests", FriendRequestViewSet, basename="friend-request")
router.register(r"", FriendViewSet, basename="friend")

urlpatterns = [
    path("", include(router.urls)),
]
