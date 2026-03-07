import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from src.apps.chat.models import Message
from src.apps.server.models import Channel, Role, Server, ServerMember
from src.apps.user.models import CustomUser


def pick(payload, camel_key, snake_key):
    return payload.get(camel_key, payload.get(snake_key))


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
    payload = response.json()
    assert len(payload["items"]) == 1
    assert pick(payload, "hasMoreOlder", "has_more_older") is False
    assert pick(payload, "hasMoreNewer", "has_more_newer") is False
    assert pick(payload, "nextBefore", "next_before") is not None
    assert pick(payload, "nextAfter", "next_after") is not None


@pytest.mark.django_db
def test_messages_list_supports_limit_and_before_cursor():
    owner = CustomUser.objects.create_user(email="owner-api3@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api3@example.com", password="pw")
    server = Server.objects.create(name="API Server 3", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    for idx in range(60):
        Message.objects.create(channel=channel, author=user, content=f"m-{idx:02d}")

    client = APIClient()
    client.force_authenticate(user=user)

    first_page = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert len(first_payload["items"]) == 50
    assert pick(first_payload, "hasMoreOlder", "has_more_older") is True
    assert pick(first_payload, "hasMoreNewer", "has_more_newer") is False
    assert pick(first_payload, "nextBefore", "next_before") is not None
    assert pick(first_payload, "nextAfter", "next_after") is not None

    older_page = client.get(
        "/api/chat/messages/",
        {
            "channel_uuid": str(channel.uuid),
            "before": pick(first_payload, "nextBefore", "next_before"),
            "limit": 50,
        },
    )
    assert older_page.status_code == 200
    older_payload = older_page.json()
    assert len(older_payload["items"]) == 10
    assert pick(older_payload, "hasMoreOlder", "has_more_older") is False
    assert pick(older_payload, "hasMoreNewer", "has_more_newer") is True


@pytest.mark.django_db
def test_messages_list_supports_after_cursor():
    owner = CustomUser.objects.create_user(email="owner-api4@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api4@example.com", password="pw")
    server = Server.objects.create(name="API Server 4", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    for idx in range(12):
        Message.objects.create(channel=channel, author=user, content=f"m-{idx:02d}")

    client = APIClient()
    client.force_authenticate(user=user)

    first_page = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid), "limit": 5})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert len(first_payload["items"]) == 5

    older_page = client.get(
        "/api/chat/messages/",
        {
            "channel_uuid": str(channel.uuid),
            "before": pick(first_payload, "nextBefore", "next_before"),
            "limit": 5,
        },
    )
    assert older_page.status_code == 200
    older_payload = older_page.json()
    assert len(older_payload["items"]) == 5

    newer_page = client.get(
        "/api/chat/messages/",
        {
            "channel_uuid": str(channel.uuid),
            "after": pick(older_payload, "nextAfter", "next_after"),
            "limit": 5,
        },
    )
    assert newer_page.status_code == 200
    newer_payload = newer_page.json()
    assert len(newer_payload["items"]) >= 1


@pytest.mark.django_db
def test_messages_list_rejects_before_and_after_together():
    owner = CustomUser.objects.create_user(email="owner-api5@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api5@example.com", password="pw")
    server = Server.objects.create(name="API Server 5", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=user, content="hello")

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(
        "/api/chat/messages/",
        {
            "channel_uuid": str(channel.uuid),
            "before": message.created_at.isoformat(),
            "after": message.created_at.isoformat(),
        },
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_messages_list_cursor_tie_break_with_same_created_at():
    owner = CustomUser.objects.create_user(email="owner-api6@example.com", password="pw")
    user = CustomUser.objects.create_user(email="member-api6@example.com", password="pw")
    server = Server.objects.create(name="API Server 6", owner=owner)
    ServerMember.objects.create(user=user, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)

    messages = [
        Message.objects.create(channel=channel, author=user, content=f"same-{idx}")
        for idx in range(3)
    ]
    same_ts = timezone.now()
    Message.objects.filter(pk__in=[message.pk for message in messages]).update(created_at=same_ts)

    client = APIClient()
    client.force_authenticate(user=user)

    first_page = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid), "limit": 2})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert len(first_payload["items"]) == 2

    second_page = client.get(
        "/api/chat/messages/",
        {
            "channel_uuid": str(channel.uuid),
            "before": pick(first_payload, "nextBefore", "next_before"),
            "limit": 2,
        },
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert len(second_payload["items"]) == 1

    seen_ids = {item["uuid"] for item in first_payload["items"]} | {
        item["uuid"] for item in second_payload["items"]
    }
    assert len(seen_ids) == 3


@pytest.mark.django_db
def test_message_patch_allows_author_and_owner():
    owner = CustomUser.objects.create_user(email="owner-api7@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-api7@example.com", password="pw")
    server = Server.objects.create(name="API Server 7", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="original")

    author_client = APIClient()
    author_client.force_authenticate(user=author)
    author_response = author_client.patch(
        f"/api/chat/messages/{message.uuid}/",
        {"content": "edited by author"},
        format="json",
    )
    assert author_response.status_code == 200
    assert author_response.json()["content"] == "edited by author"

    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    owner_response = owner_client.patch(
        f"/api/chat/messages/{message.uuid}/",
        {"content": "edited by owner"},
        format="json",
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["content"] == "edited by owner"


@pytest.mark.django_db
def test_message_patch_denies_other_member():
    owner = CustomUser.objects.create_user(email="owner-api8@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-api8@example.com", password="pw")
    intruder = CustomUser.objects.create_user(email="intruder-api8@example.com", password="pw")
    server = Server.objects.create(name="API Server 8", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    ServerMember.objects.create(user=intruder, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="original")

    intruder_client = APIClient()
    intruder_client.force_authenticate(user=intruder)
    response = intruder_client.patch(
        f"/api/chat/messages/{message.uuid}/",
        {"content": "forbidden"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_message_delete_soft_deletes_message():
    owner = CustomUser.objects.create_user(email="owner-api9@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-api9@example.com", password="pw")
    server = Server.objects.create(name="API Server 9", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="to delete")

    client = APIClient()
    client.force_authenticate(user=author)
    response = client.delete(f"/api/chat/messages/{message.uuid}/")

    assert response.status_code == 200
    payload = response.json()
    assert pick(payload, "isDeleted", "is_deleted") is True
    assert payload["content"] == ""

    message.refresh_from_db()
    assert message.is_deleted is True
    assert message.content == ""

    list_response = client.get("/api/chat/messages/", {"channel_uuid": str(channel.uuid)})
    assert list_response.status_code == 200
    assert pick(list_response.json()["items"][0], "isDeleted", "is_deleted") is True


@pytest.mark.django_db
def test_message_patch_deleted_message_returns_400():
    owner = CustomUser.objects.create_user(email="owner-api10@example.com", password="pw")
    author = CustomUser.objects.create_user(email="author-api10@example.com", password="pw")
    server = Server.objects.create(name="API Server 10", owner=owner)
    ServerMember.objects.create(user=author, server=server)
    channel = Channel.objects.create(server=server, name="general", is_public=True)
    message = Message.objects.create(channel=channel, author=author, content="to delete")
    message.is_deleted = True
    message.content = ""
    message.save(update_fields=["is_deleted", "content", "updated_at"])

    client = APIClient()
    client.force_authenticate(user=author)
    response = client.patch(
        f"/api/chat/messages/{message.uuid}/",
        {"content": "cannot edit"},
        format="json",
    )

    assert response.status_code == 400
