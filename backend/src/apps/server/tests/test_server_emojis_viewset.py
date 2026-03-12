import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from src.apps.server.models import Server, ServerEmoji, ServerMember
from src.apps.user.models import CustomUser

GIF_1X1 = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02L\x01\x00;"
)


@pytest.mark.django_db
def test_server_members_can_list_server_emojis():
    owner = CustomUser.objects.create_user(email="owner-emoji-list@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-emoji-list@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=member)
    ServerEmoji.objects.create(
        server=server,
        name="party",
        image=SimpleUploadedFile("party.gif", GIF_1X1, content_type="image/gif"),
    )

    client = APIClient()
    client.force_authenticate(user=member)
    response = client.get(f"/api/servers/{server.uuid}/emojis/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "party"
    assert ("imageUrl" in data[0] or "image_url" in data[0]) is True


@pytest.mark.django_db
def test_only_owner_can_create_server_emoji():
    owner = CustomUser.objects.create_user(email="owner-emoji-create@example.com", password="pw")
    member = CustomUser.objects.create_user(email="member-emoji-create@example.com", password="pw")
    server = Server.objects.create(name="Nest", owner=owner)
    ServerMember.objects.create(server=server, user=member)

    non_owner_client = APIClient()
    non_owner_client.force_authenticate(user=member)
    forbidden_response = non_owner_client.post(
        f"/api/servers/{server.uuid}/emojis/",
        {
            "name": "party",
            "image": SimpleUploadedFile("party.gif", GIF_1X1, content_type="image/gif"),
            "is_animated": False,
        },
        format="multipart",
    )
    assert forbidden_response.status_code == 403

    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    created_response = owner_client.post(
        f"/api/servers/{server.uuid}/emojis/",
        {
            "name": "party",
            "image": SimpleUploadedFile("party.gif", GIF_1X1, content_type="image/gif"),
            "is_animated": False,
        },
        format="multipart",
    )
    assert created_response.status_code == 201
    assert ServerEmoji.objects.filter(server=server, name="party").exists()
