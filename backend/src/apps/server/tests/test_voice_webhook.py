import base64
import hashlib
import json

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from livekit import api
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from src.apps.server.enums import ChannelType
from src.apps.server.models import Channel, Server, ServerMember, VoiceChannelOccupant
from src.apps.user.models import CustomUser
from src.asgi import application


def _ws_path_for_user(user):
    token = str(AccessToken.for_user(user))
    return f"/ws/?token={token}"


def _webhook_auth_token(body: str, api_key: str, api_secret: str) -> str:
    body_hash = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    return api.AccessToken(api_key, api_secret).with_sha256(body_hash).to_jwt()


def _participant_joined_payload(server: Server, channel: Channel, user: CustomUser) -> dict:
    return {
        "event": "participant_joined",
        "room": {"name": f"server:{server.uuid}:channel:{channel.uuid}"},
        "participant": {"identity": str(user.uuid)},
    }


@pytest.mark.django_db
@override_settings(
    LIVEKIT_API_KEY="test-livekit-key",
    LIVEKIT_WEBHOOK_SECRET="test-webhook-secret",
)
def test_voice_webhook_join_updates_occupancy_and_server_list():
    owner = CustomUser.objects.create_user(email="owner-voice-webhook@example.com", password="pw")
    guest = CustomUser.objects.create_user(email="guest-voice-webhook@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=guest)
    voice_channel = Channel.objects.create(
        server=server,
        name="Lobby",
        channel_type=ChannelType.VOICE,
    )
    text_channel = Channel.objects.create(
        server=server,
        name="general",
        channel_type=ChannelType.TEXT,
    )

    payload = _participant_joined_payload(server, voice_channel, guest)
    body = json.dumps(payload)
    client = APIClient()
    response = client.post(
        "/api/servers/livekit/webhook/",
        data=body,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {_webhook_auth_token(body, 'test-livekit-key', 'test-webhook-secret')}",
    )

    assert response.status_code == 200
    assert VoiceChannelOccupant.objects.filter(
        server=server, channel=voice_channel, user=guest
    ).exists()

    client.force_authenticate(user=owner)
    list_response = client.get("/api/servers/")
    assert list_response.status_code == 200
    channels = list_response.json()[0]["channels"]
    voice_payload = next(
        channel for channel in channels if channel["uuid"] == str(voice_channel.uuid)
    )
    text_payload = next(
        channel for channel in channels if channel["uuid"] == str(text_channel.uuid)
    )

    assert voice_payload["voice_occupants"] == [
        {
            "user_uuid": str(guest.uuid),
            "display_name": "guest-voice-webhook",
            "avatar_url": None,
        }
    ]
    assert text_payload["voice_occupants"] == []


@pytest.mark.django_db
@override_settings(
    LIVEKIT_API_KEY="test-livekit-key",
    LIVEKIT_WEBHOOK_SECRET="test-webhook-secret",
)
def test_voice_webhook_rejects_invalid_signature():
    owner = CustomUser.objects.create_user(email="owner-invalid-webhook@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    voice_channel = Channel.objects.create(
        server=server,
        name="Lobby",
        channel_type=ChannelType.VOICE,
    )
    client = APIClient()

    response = client.post(
        "/api/servers/livekit/webhook/",
        data=json.dumps(_participant_joined_payload(server, voice_channel, owner)),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalid",
    )

    assert response.status_code == 403
    assert VoiceChannelOccupant.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    LIVEKIT_API_KEY="test-livekit-key",
    LIVEKIT_WEBHOOK_SECRET="test-webhook-secret",
)
def test_voice_webhook_broadcasts_gateway_event():
    owner = CustomUser.objects.create_user(email="owner-voice-broadcast@example.com", password="pw")
    guest = CustomUser.objects.create_user(email="guest-voice-broadcast@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=guest)
    voice_channel = Channel.objects.create(
        server=server,
        name="Lobby",
        channel_type=ChannelType.VOICE,
    )
    client = APIClient()
    body = json.dumps(_participant_joined_payload(server, voice_channel, guest))
    auth_token = _webhook_auth_token(body, "test-livekit-key", "test-webhook-secret")

    async def receive_until_voice(communicator: WebsocketCommunicator):
        while True:
            event = await communicator.receive_json_from(timeout=1)
            if str(event.get("module", "")).lower() == "voice":
                return event

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(owner))
        connected, _ = await communicator.connect()
        assert connected is True

        response = await sync_to_async(client.post)(
            "/api/servers/livekit/webhook/",
            data=body,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {auth_token}",
        )
        event = await receive_until_voice(communicator)
        await communicator.disconnect()
        return response, event

    response, event = async_to_sync(scenario)()
    assert response.status_code == 200
    assert str(event["module"]).lower() == "voice"
    assert event["action"] == "members_changed"
    assert event["payload"]["server_uuid"] == str(server.uuid)
    assert event["payload"]["channel_uuid"] == str(voice_channel.uuid)
    assert event["payload"]["occupants"] == [
        {
            "user_uuid": str(guest.uuid),
            "display_name": "guest-voice-broadcast",
            "avatar_url": None,
        }
    ]
