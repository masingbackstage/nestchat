import pytest
from rest_framework.test import APIClient

from src.apps.chat.models import ChannelReadState, Message
from src.apps.server.models import Channel, Server, ServerMember
from src.apps.user.models import CustomUser


@pytest.mark.django_db
def test_read_state_get_returns_unread_count_and_mark_read_resets_it():
    owner = CustomUser.objects.create_user(email="owner-read@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-read@example.com", password="pw")
    server = Server.objects.create(name="Read Server", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    m1 = Message.objects.create(channel=channel, author=user, content="one")
    Message.objects.create(channel=channel, author=user, content="two")

    client = APIClient()
    client.force_authenticate(user=user)

    initial = client.get("/api/chat/read-state/", {"channel_uuid": str(channel.uuid)})
    assert initial.status_code == 200
    assert initial.json()["unreadCount"] == 2

    mark = client.post(
        "/api/chat/read-state/",
        {"channel_uuid": str(channel.uuid), "last_read_message_uuid": str(m1.uuid)},
        format="json",
    )
    assert mark.status_code == 200
    assert mark.json()["unreadCount"] == 1

    latest = Message.objects.filter(channel=channel).order_by("-created_at", "-uuid").first()
    mark_latest = client.post(
        "/api/chat/read-state/",
        {"channel_uuid": str(channel.uuid), "last_read_message_uuid": str(latest.uuid)},
        format="json",
    )
    assert mark_latest.status_code == 200
    assert mark_latest.json()["unreadCount"] == 0


@pytest.mark.django_db
def test_read_state_post_without_message_marks_latest_message():
    owner = CustomUser.objects.create_user(email="owner-read2@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-read2@example.com", password="pw")
    server = Server.objects.create(name="Read Server 2", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    Message.objects.create(channel=channel, author=user, content="one")
    newest = Message.objects.create(channel=channel, author=user, content="two")

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/chat/read-state/",
        {"channel_uuid": str(channel.uuid)},
        format="json",
    )

    assert response.status_code == 200
    state = ChannelReadState.objects.get(user=user, channel=channel)
    assert state.last_read_message_id == newest.uuid
    assert response.json()["unreadCount"] == 0
