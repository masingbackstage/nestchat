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


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_join_channel_allowed_returns_ack():
    owner = CustomUser.objects.create_user(email="owner-ws4@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws4@example.com", password="pw")
    server = Server.objects.create(name="WS Server 4", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "JOIN_CHANNEL",
                "payload": {"channel_uuid": str(channel.uuid)},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "ack"
    assert event["payload"]["action"] == "join_channel"
    assert event["payload"]["channel_uuid"] == str(channel.uuid)


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_join_channel_without_permission_returns_permission_denied():
    owner = CustomUser.objects.create_user(email="owner-ws5@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws5@example.com", password="pw")
    server = Server.objects.create(name="WS Server 5", owner=owner)
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
                "action": "JOIN_CHANNEL",
                "payload": {"channel_uuid": str(channel.uuid)},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "permission_denied"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_join_channel_missing_channel_returns_not_found():
    user = CustomUser.objects.create_user(email="member-ws6@example.com", password="pw")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "JOIN_CHANNEL",
                "payload": {"channel_uuid": str(uuid.uuid4())},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "not_found"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_send_message_echoes_client_id():
    owner = CustomUser.objects.create_user(email="owner-ws7@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws7@example.com", password="pw")
    server = Server.objects.create(name="WS Server 7", owner=owner)
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
                "payload": {
                    "channel_uuid": str(channel.uuid),
                    "content": "client-id",
                    "client_id": "client-123",
                },
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "new_message"
    assert event["payload"]["client_id"] == "client-123"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_edit_message_denied_for_other_member():
    owner = CustomUser.objects.create_user(email="owner-ws8@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-ws8@example.com", password="pw")
    intruder = CustomUser.objects.create_user(email="intruder-ws8@example.com", password="pw")
    server = Server.objects.create(name="WS Server 8", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    ServerMember.objects.create(user=intruder, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="original")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(intruder))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "EDIT_MESSAGE",
                "payload": {"message_uuid": str(message.uuid), "content": "forbidden"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "permission_denied"
    message.refresh_from_db()
    assert message.content == "original"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_edit_message_allowed_for_owner_broadcasts_update():
    owner = CustomUser.objects.create_user(email="owner-ws9@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-ws9@example.com", password="pw")
    server = Server.objects.create(name="WS Server 9", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="original")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(owner))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "EDIT_MESSAGE",
                "payload": {"message_uuid": str(message.uuid), "content": "updated"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "message_updated"
    assert event["payload"]["uuid"] == str(message.uuid)
    assert event["payload"]["content"] == "updated"
    message.refresh_from_db()
    assert message.content == "updated"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_delete_message_marks_message_deleted():
    owner = CustomUser.objects.create_user(email="owner-ws10@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-ws10@example.com", password="pw")
    server = Server.objects.create(name="WS Server 10", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="to-delete")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(author))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "DELETE_MESSAGE",
                "payload": {"message_uuid": str(message.uuid)},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "message_deleted"
    assert event["payload"]["uuid"] == str(message.uuid)
    assert event["payload"]["is_deleted"] is True
    assert event["payload"]["content"] == ""
    message.refresh_from_db()
    assert message.is_deleted is True
