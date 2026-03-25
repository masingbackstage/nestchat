import json
import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework_simplejwt.tokens import AccessToken

from src.apps.chat.models import Message
from src.apps.dm.models import DMConversation, DMMessage
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
def test_ws_send_dm_message_without_client_id_persists_message():
    author = CustomUser.objects.create_user(email="author-dm-ws1@example.com", password="pw")
    recipient = CustomUser.objects.create_user(email="recipient-dm-ws1@example.com", password="pw")
    conversation = DMConversation.objects.create(conversation_type=DMConversation.TYPE_DIRECT)
    conversation.participants.add(author, recipient)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(author))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_DM_MESSAGE",
                "payload": {
                    "conversation_uuid": str(conversation.uuid),
                    "content": "hello dm",
                },
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "dm_new_message"
    assert event["payload"]["conversation_uuid"] == str(conversation.uuid)
    assert event["payload"]["content"] == "hello dm"
    assert "client_id" not in event["payload"]

    messages = list(DMMessage.objects.filter(conversation=conversation))
    assert len(messages) == 1
    assert messages[0].content == "hello dm"
    assert messages[0].author_id == author.pk


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_send_dm_message_echoes_client_id():
    author = CustomUser.objects.create_user(email="author-dm-ws2@example.com", password="pw")
    recipient = CustomUser.objects.create_user(email="recipient-dm-ws2@example.com", password="pw")
    conversation = DMConversation.objects.create(conversation_type=DMConversation.TYPE_DIRECT)
    conversation.participants.add(author, recipient)

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(author))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "SEND_DM_MESSAGE",
                "payload": {
                    "conversation_uuid": str(conversation.uuid),
                    "content": "hello dm client",
                    "client_id": "dm-client-123",
                },
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "dm_new_message"
    assert event["payload"]["client_id"] == "dm-client-123"
    assert (
        DMMessage.objects.filter(conversation=conversation, content="hello dm client").count() == 1
    )


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


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_presence_status_changed_broadcasts_to_other_server_members():
    owner = CustomUser.objects.create_user(email="owner-presence@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-presence@example.com", password="pw")
    server = Server.objects.create(name="Presence Server", owner=owner)
    ServerMember.objects.create(user=member, server=server)

    async def scenario():
        owner_communicator = WebsocketCommunicator(application, _ws_path_for_user(owner))
        connected_owner, _ = await owner_communicator.connect()
        assert connected_owner is True

        member_communicator = WebsocketCommunicator(application, _ws_path_for_user(member))
        connected_member, _ = await member_communicator.connect()
        assert connected_member is True

        connected_events = [
            await owner_communicator.receive_json_from(timeout=1),
            await owner_communicator.receive_json_from(timeout=1),
            await owner_communicator.receive_json_from(timeout=1),
            await owner_communicator.receive_json_from(timeout=1),
        ]

        await member_communicator.disconnect()
        disconnected_events = [
            await owner_communicator.receive_json_from(timeout=1),
            await owner_communicator.receive_json_from(timeout=1),
        ]

        await owner_communicator.disconnect()
        return connected_events, disconnected_events

    connected_events, disconnected_events = async_to_sync(scenario)()
    connected_status_event = next(
        event
        for event in connected_events
        if event["action"] == "status_changed"
        and event["payload"]["member_uuid"] == str(member.uuid)
    )
    connected_members_changed_event = next(
        event for event in connected_events if event["action"] == "members_changed"
    )
    disconnected_status_event = next(
        event for event in disconnected_events if event["action"] == "status_changed"
    )
    disconnected_members_changed_event = next(
        event for event in disconnected_events if event["action"] == "members_changed"
    )

    assert str(connected_status_event["module"]).lower() == "presence"
    assert connected_status_event["payload"]["server_uuid"] == str(server.uuid)
    assert connected_status_event["payload"]["member_uuid"] == str(member.uuid)
    assert connected_status_event["payload"]["is_online"] is True

    assert str(connected_members_changed_event["module"]).lower() == "presence"
    assert connected_members_changed_event["payload"]["server_uuid"] == str(server.uuid)
    assert connected_members_changed_event["payload"]["reason"] == "presence_changed"

    assert str(disconnected_status_event["module"]).lower() == "presence"
    assert disconnected_status_event["payload"]["server_uuid"] == str(server.uuid)
    assert disconnected_status_event["payload"]["member_uuid"] == str(member.uuid)
    assert disconnected_status_event["payload"]["is_online"] is False

    assert str(disconnected_members_changed_event["module"]).lower() == "presence"
    assert disconnected_members_changed_event["payload"]["server_uuid"] == str(server.uuid)
    assert disconnected_members_changed_event["payload"]["reason"] == "presence_changed"


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_toggle_reaction_broadcasts_updated_snapshot():
    owner = CustomUser.objects.create_user(email="owner-ws11@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-ws11@example.com", password="pw")
    server = Server.objects.create(name="WS Server 11", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user, content="hello")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(user))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "TOGGLE_REACTION",
                "payload": {"message_uuid": str(message.uuid), "emoji": "👍"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert str(event["module"]).lower() == "chat"
    assert event["action"] == "message_reactions_updated"
    assert event["payload"]["uuid"] == str(message.uuid)
    reactions = event["payload"]["reactions"]
    assert len(reactions) == 1
    assert reactions[0]["emoji"] == "👍"
    assert reactions[0]["count"] == 1
    assert reactions[0]["reacted_by_me"] is True


@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
def test_ws_toggle_reaction_denied_without_access():
    owner = CustomUser.objects.create_user(email="owner-ws12@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-ws12@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="outsider-ws12@example.com", password="pw")
    server = Server.objects.create(name="WS Server 12", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="hello")

    async def scenario():
        communicator = WebsocketCommunicator(application, _ws_path_for_user(outsider))
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.send_json_to(
            {
                "module": "CHAT",
                "action": "TOGGLE_REACTION",
                "payload": {"message_uuid": str(message.uuid), "emoji": "👍"},
            }
        )
        event = await communicator.receive_json_from(timeout=1)
        await communicator.disconnect()
        return event

    event = async_to_sync(scenario)()
    assert event["module"] == "system"
    assert event["action"] == "error"
    assert event["payload"]["code"] == "permission_denied"
