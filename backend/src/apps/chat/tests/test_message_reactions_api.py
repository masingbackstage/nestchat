import pytest
from rest_framework.test import APIClient

from src.apps.chat.models import Message
from src.apps.server.models import Channel, Server, ServerMember
from src.apps.user.models import CustomUser


def pick(payload, camel_key, snake_key):
    return payload.get(camel_key, payload.get(snake_key))


@pytest.mark.django_db
def test_toggle_reaction_adds_then_removes():
    owner = CustomUser.objects.create_user(email="owner-r1@example.com", password="pw")
    user = CustomUser.objects.create_user(email="user-r1@example.com", password="pw")
    server = Server.objects.create(name="R Server 1", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user, content="hello")

    client = APIClient()
    client.force_authenticate(user=user)

    first = client.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "👍"},
        format="json",
    )
    assert first.status_code == 200
    first_reactions = first.json().get("reactions", [])
    assert len(first_reactions) == 1
    assert first_reactions[0]["emoji"] == "👍"
    assert first_reactions[0]["count"] == 1
    assert pick(first_reactions[0], "reactedByMe", "reacted_by_me") is True

    second = client.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "👍"},
        format="json",
    )
    assert second.status_code == 200
    assert second.json().get("reactions", []) == []


@pytest.mark.django_db
def test_toggle_reaction_counts_two_users():
    owner = CustomUser.objects.create_user(email="owner-r2@example.com", password="pw")
    user_a = CustomUser.objects.create_user(email="usera-r2@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="userb-r2@example.com", password="pw")
    server = Server.objects.create(name="R Server 2", owner=owner)
    ServerMember.objects.create(user=user_a, server=server)
    ServerMember.objects.create(user=user_b, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user_a, content="hello")

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)
    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    assert (
        client_a.post(
            f"/api/chat/messages/{message.uuid}/reactions/toggle/",
            {"emoji": "🎉"},
            format="json",
        ).status_code
        == 200
    )
    second = client_b.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "🎉"},
        format="json",
    )
    assert second.status_code == 200

    reactions = second.json()["reactions"]
    assert reactions[0]["emoji"] == "🎉"
    assert reactions[0]["count"] == 2
    assert pick(reactions[0], "reactedByMe", "reacted_by_me") is True


@pytest.mark.django_db
def test_toggle_reaction_accepts_unicode_emoji_outside_old_whitelist():
    owner = CustomUser.objects.create_user(email="owner-r3@example.com", password="pw")
    user = CustomUser.objects.create_user(email="user-r3@example.com", password="pw")
    server = Server.objects.create(name="R Server 3", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user, content="hello")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "🚀"},
        format="json",
    )
    assert response.status_code == 200
    reactions = response.json()["reactions"]
    assert len(reactions) == 1
    assert reactions[0]["emoji"] == "🚀"


@pytest.mark.django_db
def test_toggle_reaction_denies_user_without_access():
    owner = CustomUser.objects.create_user(email="owner-r4@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-r4@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="outsider-r4@example.com", password="pw")
    server = Server.objects.create(name="R Server 4", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="hello")

    client = APIClient()
    client.force_authenticate(user=outsider)
    response = client.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "👍"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_toggle_reaction_rejects_deleted_message():
    owner = CustomUser.objects.create_user(email="owner-r5@example.com", password="pw")
    user = CustomUser.objects.create_user(email="user-r5@example.com", password="pw")
    server = Server.objects.create(name="R Server 5", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user, content="")
    message.is_deleted = True
    message.save(update_fields=["is_deleted"])

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/chat/messages/{message.uuid}/reactions/toggle/",
        {"emoji": "👍"},
        format="json",
    )
    assert response.status_code == 400
