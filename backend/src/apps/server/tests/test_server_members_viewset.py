import pytest
from rest_framework.test import APIClient

from src.apps.server.models import Role, Server, ServerMember
from src.apps.user.models import CustomUser


def pick(payload, camel_key, snake_key):
    return payload.get(camel_key, payload.get(snake_key))


@pytest.mark.django_db
def test_server_members_returns_grouped_members_for_owner():
    owner = CustomUser.objects.create_user(email="owner-members@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-members@example.com", password="pw")
    no_role_member = CustomUser.objects.create_user(
        email="plain-members@example.com", password="pw"
    )
    server = Server.objects.create(name="Nest", owner=owner)
    member_link = ServerMember.objects.create(server=server, user=member)
    ServerMember.objects.create(server=server, user=no_role_member)

    role_beta = Role.objects.create(server=server, name="Beta")
    role_alpha = Role.objects.create(server=server, name="Alpha")
    member_link.roles.add(role_beta, role_alpha)

    owner.profile.display_name = "Owner Name"
    owner.profile.save(update_fields=["display_name"])
    member.profile.display_name = "Member Name"
    member.profile.custom_status = "Reviewing PRs"
    member.profile.is_online = True
    member.profile.save(update_fields=["display_name", "custom_status", "is_online"])
    no_role_member.profile.is_online = True
    no_role_member.profile.save(update_fields=["is_online"])

    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.get(f"/api/servers/{server.uuid}/members/")

    assert response.status_code == 200
    payload = response.json()
    groups = payload["groups"]

    online_with_roles_group = next(group for group in groups if group["label"] == "Online — roles")
    online_group = next(group for group in groups if group["label"] == "Online")
    offline_group = next(group for group in groups if group["label"] == "Offline")

    member_payload = next(
        item for item in online_with_roles_group["members"] if str(item["uuid"]) == str(member.uuid)
    )
    assert pick(member_payload, "displayName", "display_name") == "Member Name"
    assert pick(member_payload, "isOnline", "is_online") is True
    assert pick(member_payload, "customStatus", "custom_status") == "Reviewing PRs"
    assert [role["name"] for role in member_payload["roles"]] == ["Alpha", "Beta"]

    owner_payload = next(
        item for item in offline_group["members"] if str(item["uuid"]) == str(owner.uuid)
    )
    assert pick(owner_payload, "displayName", "display_name") == "Owner Name"

    plain_payload = next(
        item for item in online_group["members"] if str(item["uuid"]) == str(no_role_member.uuid)
    )
    assert pick(plain_payload, "displayName", "display_name") == "plain-members"

    all_member_uuids = [
        str(member_item["uuid"]) for group in groups for member_item in group["members"]
    ]
    assert len(all_member_uuids) == len(set(all_member_uuids))


@pytest.mark.django_db
def test_server_members_member_can_access():
    owner = CustomUser.objects.create_user(email="owner-members-2@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-members-2@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=member)

    client = APIClient()
    client.force_authenticate(user=member)
    response = client.get(f"/api/servers/{server.uuid}/members/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_server_members_outsider_forbidden():
    owner = CustomUser.objects.create_user(email="owner-members-3@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="outsider-members-3@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)

    client = APIClient()
    client.force_authenticate(user=outsider)
    response = client.get(f"/api/servers/{server.uuid}/members/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_server_members_missing_server_returns_404():
    user = CustomUser.objects.create_user(email="missing-members@example.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/servers/6c307146-2faf-41b7-a2ca-7b11e8c8585f/members/")
    assert response.status_code == 404
