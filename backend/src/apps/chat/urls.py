from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChannelReadStateAPIView, MessageViewSet

router = DefaultRouter()

router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
    path("read-state/", ChannelReadStateAPIView.as_view(), name="chat-read-state"),
]
