import pytest

from src.apps.chat.services import (
    MessageNotFound,
    MessagePermissionDenied,
    get_message_for_user_or_raise,
)
from src.apps.chat.models import Message
from src.apps.server.models import Channel, Server, ServerMember
from src.apps.user.models import CustomUser


@pytest.mark.django_db
def test_get_message_for_user_allows_author():
    owner = CustomUser.objects.create_user(email="owner-mp1@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-mp1@example.com", password="pw")
    server = Server.objects.create(name="MP Server 1", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="hello")

    resolved = get_message_for_user_or_raise(author, message.uuid)
    assert resolved.uuid == message.uuid


@pytest.mark.django_db
def test_get_message_for_user_allows_server_owner():
    owner = CustomUser.objects.create_user(email="owner-mp2@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-mp2@example.com", password="pw")
    server = Server.objects.create(name="MP Server 2", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="hello")

    resolved = get_message_for_user_or_raise(owner, message.uuid)
    assert resolved.uuid == message.uuid


@pytest.mark.django_db
def test_get_message_for_user_denies_other_member():
    owner = CustomUser.objects.create_user(email="owner-mp3@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-mp3@example.com", password="pw")
    intruder = CustomUser.objects.create_user(email="intruder-mp3@example.com", password="pw")
    server = Server.objects.create(name="MP Server 3", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    ServerMember.objects.create(user=intruder, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="hello")

    with pytest.raises(MessagePermissionDenied) as exc:
        get_message_for_user_or_raise(intruder, message.uuid)

    assert exc.value.code == "permission_denied"


@pytest.mark.django_db
def test_get_message_for_user_missing_message():
    user = CustomUser.objects.create_user(email="user-mp4@example.com", password="pw")
    with pytest.raises(MessageNotFound):
        get_message_for_user_or_raise(user, "00000000-0000-0000-0000-000000000000")
