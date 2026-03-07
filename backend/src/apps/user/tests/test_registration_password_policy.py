import pytest
from rest_framework.test import APIClient

REGISTRATION_URL = "/api/auth/registration/"
WEAK_PASSWORD_ERROR = (
    "Password must be at least 10 characters long and include lowercase, uppercase, "
    "digit, and special character."
)


def register_payload(email, password):
    return {
        "email": email,
        "password1": password,
        "password2": password,
        "display_name": "Tester",
    }


def extract_error_messages(payload):
    messages = []
    for value in payload.values():
        if isinstance(value, list):
            messages.extend(str(item) for item in value)
        elif isinstance(value, str):
            messages.append(value)
    return messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password",
    [
        "Ab1!xyz",  # < 10 chars
        "abcdefg123!",  # no uppercase
        "ABCDEFG123!",  # no lowercase
        "Abcdefghij!",  # no digit
        "Abcdefg1234",  # no special
    ],
)
def test_registration_rejects_password_without_required_complexity(password):
    client = APIClient()

    response = client.post(
        REGISTRATION_URL,
        register_payload(email=f"weak-{password}@example.com", password=password),
        format="json",
    )

    assert response.status_code == 400
    payload = response.json()
    errors = extract_error_messages(payload)
    assert any(WEAK_PASSWORD_ERROR in error for error in errors)


@pytest.mark.django_db
def test_registration_accepts_valid_strong_password():
    client = APIClient()

    response = client.post(
        REGISTRATION_URL,
        register_payload(email="strong@example.com", password="ValidPass1!"),
        format="json",
    )

    assert response.status_code == 201


@pytest.mark.django_db
def test_registration_keeps_similarity_validator_active():
    client = APIClient()

    response = client.post(
        REGISTRATION_URL,
        register_payload(email="johnsmith@example.com", password="Johnsmith1!"),
        format="json",
    )

    assert response.status_code == 400
    payload = response.json()
    errors = extract_error_messages(payload)
    assert any("too similar" in error.lower() for error in errors)
