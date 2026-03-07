import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from src.apps.chat.models import Message
from src.apps.chat.views import MessageViewSet
from src.apps.server.models import Channel, Server, ServerMember
from src.apps.user.models import CustomUser
from src.asgi import application


def _ws_path_for_user(user):
    token = str(AccessToken.for_user(user))
    return f"/ws/?token={token}"


@pytest.mark.django_db
def test_logout_all_blacklists_user_refresh_tokens():
    user = CustomUser.objects.create_user(email="logout-all@example.com", password="pw")
    RefreshToken.for_user(user)
    RefreshToken.for_user(user)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post("/api/auth/logout-all/")

    assert response.status_code == 200
    assert response.json()["detail"] == "All refresh tokens have been revoked."
    outstanding_count = OutstandingToken.objects.filter(user=user).count()
    blacklisted_count = BlacklistedToken.objects.filter(token__user=user).count()
    assert outstanding_count == blacklisted_count


@pytest.mark.django_db
def test_refresh_rotation_invalidates_previous_refresh_token():
    user = CustomUser.objects.create_user(email="refresh-rotation@example.com", password="pw")
    refresh = RefreshToken.for_user(user)

    client = APIClient()
    first = client.post("/api/auth/token/refresh/", {"refresh": str(refresh)}, format="json")
    assert first.status_code == 200
    refreshed_token = first.json().get("refresh")
    assert refreshed_token

    second = client.post("/api/auth/token/refresh/", {"refresh": str(refresh)}, format="json")
    assert second.status_code in {400, 401}


@pytest.mark.django_db
def test_logout_session_blacklists_only_current_refresh_token():
    user = CustomUser.objects.create_user(email="logout-session@example.com", password="pw")
    first_refresh = RefreshToken.for_user(user)
    second_refresh = RefreshToken.for_user(user)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/auth/logout-session/",
        {"refresh": str(first_refresh)},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Session logged out."

    first_reuse = APIClient().post(
        "/api/auth/token/refresh/", {"refresh": str(first_refresh)}, format="json"
    )
    second_reuse = APIClient().post(
        "/api/auth/token/refresh/", {"refresh": str(second_refresh)}, format="json"
    )
    assert first_reuse.status_code in {400, 401}
    assert second_reuse.status_code == 200


@pytest.mark.django_db
def test_messages_endpoint_is_throttled_by_scope(monkeypatch):
    owner = CustomUser.objects.create_user(email="owner-throttle@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-throttle@example.com", password="pw")
    server = Server.objects.create(name="Throttle Server", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    Message.objects.create(channel=channel, author=user, content="hello")

    client = APIClient()
    client.force_authenticate(user=user)

    monkeypatch.setattr(MessageViewSet, "throttle_classes", [ScopedRateThrottle])
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"chat_reads": "1/min"})

    with override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}):
        first = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})
        second = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.django_db(transaction=True)
@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    GATEWAY_SEND_MESSAGE_RATE_LIMIT_PER_MINUTE=1,
    GATEWAY_RATE_LIMIT_WINDOW_SECONDS=60,
)
def test_ws_send_message_rate_limited_after_limit_exceeded():
    owner = CustomUser.objects.create_user(email="owner-ws-limit@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws-limit@example.com", password="pw")
    server = Server.objects.create(name="WS Limit Server", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_MESSAGE",
                "payload": {"channel_uuid": str(channel.uuid), "content": "first"},
            }
        )
        first_event = await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_MESSAGE",
                "payload": {"channel_uuid": str(channel.uuid), "content": "second"},
            }
        )
        second_event = await communicator.receive_json_from(timeout=1)

        await communicator.disconnect()
        return first_event, second_event

    first_event, second_event = async_to_sync(scenario)()

    assert str(first_event["module"]).lower() == "chat"
    assert first_event["action"] == "new_message"
    assert second_event["module"] == "system"
    assert second_event["action"] == "error"
    assert second_event["payload"]["code"] == "rate_limited"
    assert Message.objects.filter(channel=channel).count() == 1
