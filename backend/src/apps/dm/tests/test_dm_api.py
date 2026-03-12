import pytest
from rest_framework.test import APIClient

from src.apps.dm.models import DMConversation, DMMessage
from src.apps.friends.models import Friendship
from src.apps.user.models import CustomUser


def pick(payload, camel_key, snake_key):
    return payload.get(camel_key, payload.get(snake_key))


@pytest.mark.django_db
def test_create_direct_conversation_is_deduplicated():
    user_a = CustomUser.objects.create_user(email="a@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="b@example.com", password="pw")

    client = APIClient()
    client.force_authenticate(user=user_a)

    first = client.post(
        "/api/dm/conversations/",
        {"participant_uuids": [str(user_b.uuid)]},
        format="json",
    )
    assert first.status_code == 201

    second = client.post(
        "/api/dm/conversations/",
        {"participant_uuids": [str(user_b.uuid)]},
        format="json",
    )
    assert second.status_code == 201

    assert DMConversation.objects.count() == 1


@pytest.mark.django_db
def test_dm_messages_permissions_and_pagination():
    user_a = CustomUser.objects.create_user(email="a2@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="b2@example.com", password="pw")
    outsider = CustomUser.objects.create_user(email="c2@example.com", password="pw")

    conversation = DMConversation.objects.create(conversation_type=DMConversation.TYPE_DIRECT)
    conversation.participants.add(user_a, user_b)

    for idx in range(12):
        DMMessage.objects.create(conversation=conversation, author=user_a, content=f"m-{idx:02d}")

    client = APIClient()
    client.force_authenticate(user=user_b)
    response = client.get(f"/api/dm/conversations/{conversation.uuid}/messages/?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 5
    assert pick(payload, "hasMoreOlder", "has_more_older") is True

    outsider_client = APIClient()
    outsider_client.force_authenticate(user=outsider)
    denied = outsider_client.get(f"/api/dm/conversations/{conversation.uuid}/messages/")
    assert denied.status_code == 403


@pytest.mark.django_db
def test_dm_message_edit_delete_author_only():
    user_a = CustomUser.objects.create_user(email="a3@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="b3@example.com", password="pw")

    conversation = DMConversation.objects.create(conversation_type=DMConversation.TYPE_DIRECT)
    conversation.participants.add(user_a, user_b)
    message = DMMessage.objects.create(conversation=conversation, author=user_a, content="hello")

    author_client = APIClient()
    author_client.force_authenticate(user=user_a)
    patch_response = author_client.patch(
        f"/api/dm/messages/{message.uuid}/",
        {"content": "edited"},
        format="json",
    )
    assert patch_response.status_code == 200

    other_client = APIClient()
    other_client.force_authenticate(user=user_b)
    denied_patch = other_client.patch(
        f"/api/dm/messages/{message.uuid}/",
        {"content": "x"},
        format="json",
    )
    assert denied_patch.status_code == 403

    delete_response = author_client.delete(f"/api/dm/messages/{message.uuid}/")
    assert delete_response.status_code == 200
    assert delete_response.json().get("isDeleted", delete_response.json().get("is_deleted")) is True


@pytest.mark.django_db
def test_create_direct_conversation_endpoint_requires_accepted_friendship():
    user_a = CustomUser.objects.create_user(email="a4@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="b4@example.com", password="pw")

    client = APIClient()
    client.force_authenticate(user=user_a)

    denied = client.post(
        "/api/dm/conversations/direct/",
        {"user_uuid": str(user_b.uuid)},
        format="json",
    )
    assert denied.status_code == 403

    low, high = Friendship.normalize_pair(user_a, user_b)
    Friendship.objects.create(
        user_low=low,
        user_high=high,
        requester=user_a,
        addressee=user_b,
        status=Friendship.Status.ACCEPTED,
    )

    allowed = client.post(
        "/api/dm/conversations/direct/",
        {"user_uuid": str(user_b.uuid)},
        format="json",
    )
    assert allowed.status_code == 200
    assert allowed.json().get("conversationType", allowed.json().get("conversation_type")) == "DIRECT"
