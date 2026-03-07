import uuid

import pytest

from src.apps.chat.services import (
    ChannelNotFound,
    ChannelPermissionDenied,
    get_channel_for_user_or_raise,
)
from src.apps.server.models import Channel, Role, Server, ServerMember
from src.apps.user.models import CustomUser


@pytest.mark.django_db
def test_public_channel_member_is_allowed():
    owner = CustomUser.objects.create_user(email="owner@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member@example.com", password="pw")
    server = Server.objects.create(name="S", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    resolved = get_channel_for_user_or_raise(user, channel.uuid)

    assert resolved.uuid == channel.uuid


@pytest.mark.django_db
def test_private_channel_without_role_is_denied():
    owner = CustomUser.objects.create_user(email="owner2@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member2@example.com", password="pw")
    server = Server.objects.create(name="S2", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="secret", is_public=False)
    role = Role.objects.create(server=server, name="vip")
    channel.allowed_roles.add(role)

    with pytest.raises(ChannelPermissionDenied) as exc:
        get_channel_for_user_or_raise(user, channel.uuid)

    assert exc.value.code == "permission_denied"
    assert exc.value.detail == "Permission denied."


@pytest.mark.django_db
def test_missing_channel_raises_not_found():
    user = CustomUser.objects.create_user(email="user3@example.com", password="pw")

    with pytest.raises(ChannelNotFound) as exc:
        get_channel_for_user_or_raise(user, uuid.uuid4())

    assert exc.value.code == "not_found"
    assert exc.value.detail == "Channel not found."


@pytest.mark.django_db
def test_user_outside_server_is_denied():
    owner = CustomUser.objects.create_user(email="owner4@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="outsider4@example.com", password="pw")
    server = Server.objects.create(name="S4", owner=owner)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    with pytest.raises(ChannelPermissionDenied) as exc:
        get_channel_for_user_or_raise(outsider, channel.uuid)

    assert exc.value.code == "permission_denied"
    assert exc.value.detail == "Permission denied."
