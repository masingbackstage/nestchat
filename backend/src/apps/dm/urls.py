from django.urls import include, path
from rest_framework.routers import DefaultRouter

from src.apps.dm.views import DMConversationViewSet, DMMessageViewSet

router = DefaultRouter()
router.register(r"conversations", DMConversationViewSet, basename="dm-conversation")
router.register(r"messages", DMMessageViewSet, basename="dm-message")

urlpatterns = [
    path("", include(router.urls)),
]
