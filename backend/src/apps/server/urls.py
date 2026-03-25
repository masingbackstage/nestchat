from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LiveKitWebhookView, ServerViewSet

router = DefaultRouter()
router.register(r"", ServerViewSet, basename="server")

urlpatterns = [
    path("livekit/webhook/", LiveKitWebhookView.as_view(), name="livekit-webhook"),
    path("", include(router.urls)),
]
