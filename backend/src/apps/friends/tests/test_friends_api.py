import pytest
from rest_framework.test import APIClient

from src.apps.friends.models import Friendship
from src.apps.user.models import CustomUser


@pytest.mark.django_db
def test_send_friend_request_and_accept_flow():
    sender = CustomUser.objects.create_user(email="sender@example.com", password="pw")
    receiver = CustomUser.objects.create_user(email="receiver@example.com", password="pw")

    sender_client = APIClient()
    sender_client.force_authenticate(user=sender)

    create_response = sender_client.post(
        "/api/friends/requests/",
        {"user_uuid": str(receiver.uuid)},
        format="json",
    )
    assert create_response.status_code == 201

    relation_uuid = create_response.json()["uuid"]

    receiver_client = APIClient()
    receiver_client.force_authenticate(user=receiver)
    accept_response = receiver_client.post(f"/api/friends/requests/{relation_uuid}/accept/")
    assert accept_response.status_code == 200

    friends_response = sender_client.get("/api/friends/")
    assert friends_response.status_code == 200
    assert len(friends_response.json()) == 1


@pytest.mark.django_db
def test_friend_request_rejects_self_and_duplicate_pending():
    user = CustomUser.objects.create_user(email="self@example.com", password="pw")
    other = CustomUser.objects.create_user(email="other@example.com", password="pw")

    client = APIClient()
    client.force_authenticate(user=user)

    self_response = client.post(
        "/api/friends/requests/",
        {"user_uuid": str(user.uuid)},
        format="json",
    )
    assert self_response.status_code == 400

    first = client.post(
        "/api/friends/requests/",
        {"user_uuid": str(other.uuid)},
        format="json",
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/friends/requests/",
        {"user_uuid": str(other.uuid)},
        format="json",
    )
    assert duplicate.status_code == 400


@pytest.mark.django_db
def test_user_search_requires_query_and_returns_matches():
    requester = CustomUser.objects.create_user(email="req@example.com", password="pw")
    target = CustomUser.objects.create_user(email="johnsmith@example.com", password="pw")
    target.profile.display_name = "John Smith"
    target.profile.save(update_fields=["display_name"])

    client = APIClient()
    client.force_authenticate(user=requester)

    too_short = client.get("/api/users/search/?q=j")
    assert too_short.status_code == 200
    assert too_short.json() == []

    search_response = client.get("/api/users/search/?q=john")
    assert search_response.status_code == 200
    assert any(item["uuid"] == str(target.uuid) for item in search_response.json())


@pytest.mark.django_db
def test_remove_friend_relation_sets_canceled():
    user_a = CustomUser.objects.create_user(email="a@example.com", password="pw")
    user_b = CustomUser.objects.create_user(email="b@example.com", password="pw")

    low, high = Friendship.normalize_pair(user_a, user_b)
    relation = Friendship.objects.create(
        user_low=low,
        user_high=high,
        requester=user_a,
        addressee=user_b,
        status=Friendship.Status.ACCEPTED,
    )

    client = APIClient()
    client.force_authenticate(user=user_b)
    response = client.delete(f"/api/friends/{relation.uuid}/")
    assert response.status_code == 200

    relation.refresh_from_db()
    assert relation.status == Friendship.Status.CANCELED
