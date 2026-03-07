import json
import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework_simplejwt.tokens import AccessToken

from src.apps.chat.models import Message
from src.apps.server.models import Channel, Role, Server, ServerMember
from src.apps.user.models import CustomUser
from src.asgi import application


def _ws_path_for_user(user):
    token = str(AccessToken.for_user(user))
    return f"/ws/?token={token}"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_send_message_denied_without_role():
    owner = CustomUser.objects.create_user(email="owner-ws@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws@example.com", password="pw")
    server = Server.objects.create(name="WS Server", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="private", is_public=False)
    role = Role.objects.create(server=server, name="allowed")
    channel.allowed_roles.add(role)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_MESSAGE",
                "payload": {"channel_uuid": str(channel.uuid), "content": "forbidden"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "permission_denied"
    assert Message.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_send_message_allowed_with_role():
    owner = CustomUser.objects.create_user(email="owner-ws2@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws2@example.com", password="pw")
    server = Server.objects.create(name="WS Server 2", owner=owner)
    member = ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="private", is_public=False)
    role = Role.objects.create(server=server, name="allowed")
    member.roles.add(role)
    channel.allowed_roles.add(role)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_MESSAGE",
                "payload": {"channel_uuid": str(channel.uuid), "content": "allowed"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "new_message"
    assert event["payload"]["channel_id"] == str(channel.uuid)
    assert Message.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_send_message_missing_channel_returns_not_found_error():
    user = CustomUser.objects.create_user(email="member-ws3@example.com", password="pw")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_MESSAGE",
                "payload": {"channel_uuid": str(uuid.uuid4()), "content": "missing"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "not_found"
    assert Message.objects.count() == 0
