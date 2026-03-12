import pytest
from rest_framework.test import APIClient

from src.apps.server.models import Channel, Role, Server, ServerMember
from src.apps.user.models import CustomUser


def pick(payload, camel_key, snake_key):
    return payload.get(camel_key, payload.get(snake_key))


def create_payload(**overrides):
    payload = {
        "name": "announcements",
        "channel_emoji": "",
        "channel_type": "TEXT",
        "topic": "Server updates",
        "is_public": False,
        "allowed_roles": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_owner_can_create_channel():
    owner = CustomUser.objects.create_user(email="owner-create@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    role = Role.objects.create(server=server, name="mods")

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(allowed_roles=[str(role.uuid)]),
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "announcements"
    assert pick(payload, "channelType", "channel_type") == "TEXT"
    assert pick(payload, "isPublic", "is_public") is False
    assert pick(payload, "allowedRoles", "allowed_roles") == [str(role.uuid)]
    assert Channel.objects.filter(server=server, name="announcements").exists()


@pytest.mark.django_db
def test_owner_can_create_channel_with_channel_emoji():
    owner = CustomUser.objects.create_user(email="owner-emoji-channel@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(channel_emoji="🚀"),
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert pick(payload, "channelEmoji", "channel_emoji") == "🚀"


@pytest.mark.django_db
def test_member_cannot_create_channel():
    owner = CustomUser.objects.create_user(email="owner-member@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-create@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=member)

    client = APIClient()
    client.force_authenticate(user=member)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_non_member_cannot_create_channel():
    owner = CustomUser.objects.create_user(email="owner-non-member@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="outsider-create@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)

    client = APIClient()
    client.force_authenticate(user=outsider)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_missing_server_returns_not_found():
    user = CustomUser.objects.create_user(email="missing-server@example.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/servers/43e0bbca-c52b-4d7a-8627-b5b2cbf0047f/channels/",
        create_payload(),
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_invalid_payload_returns_bad_request():
    owner = CustomUser.objects.create_user(email="owner-invalid@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(channel_type="INVALID"),
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_allowed_roles_must_belong_to_server():
    owner = CustomUser.objects.create_user(email="owner-roles@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)

    other_owner = CustomUser.objects.create_user(
        email="owner-other-server@example.com", password="pw"
    )
    other_server = Server.objects.create(name="Other", owner=other_owner)
    foreign_role = Role.objects.create(server=other_server, name="foreign")

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(allowed_roles=[str(foreign_role.uuid)]),
        format="json",
    )

    assert response.status_code == 400
    errors = response.json()
    assert "allowedRoles" in errors or "allowed_roles" in errors


@pytest.mark.django_db
def test_public_channel_ignores_allowed_roles():
    owner = CustomUser.objects.create_user(email="owner-public@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    role = Role.objects.create(server=server, name="mods")

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(is_public=True, allowed_roles=[str(role.uuid)]),
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert pick(payload, "allowedRoles", "allowed_roles") == []


@pytest.mark.django_db
def test_servers_list_still_works_after_channel_creation():
    owner = CustomUser.objects.create_user(email="owner-list@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    client = APIClient()
    client.force_authenticate(user=owner)

    create_response = client.post(
        f"/api/servers/{server.uuid}/channels/",
        create_payload(name="general", is_public=True),
        format="json",
    )
    assert create_response.status_code == 201

    list_response = client.get("/api/servers/")
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert pick(data[0], "isOwner", "is_owner") is True
    channels = data[0]["channels"]
    assert any(channel["name"] == "general" for channel in channels)
