import pytest
from rest_framework.test import APIClient

from src.apps.chat.models import Message
from src.apps.server.models import Channel, Role, Server, ServerMember
from src.apps.user.models import CustomUser


@pytest.mark.django_db
def test_messages_list_denies_user_without_private_channel_role():
    owner = CustomUser.objects.create_user(email="owner-api@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api@example.com", password="pw")
    server = Server.objects.create(name="API Server", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="private", is_public=False)
    role = Role.objects.create(server=server, name="allowed")
    channel.allowed_roles.add(role)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})

    assert response.status_code == 403


@pytest.mark.django_db
def test_messages_list_allows_member_with_private_channel_role():
    owner = CustomUser.objects.create_user(email="owner-api2@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api2@example.com", password="pw")
    server = Server.objects.create(name="API Server 2", owner=owner)
    member = ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="private", is_public=False)
    role = Role.objects.create(server=server, name="allowed")
    member.roles.add(role)
    channel.allowed_roles.add(role)
    Message.objects.create(channel=channel, author=user, content="hello")

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})

    assert response.status_code == 200
    assert len(response.json()) == 1
