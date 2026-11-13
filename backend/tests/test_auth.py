"""Registration and login. Every test creates its own user, so order doesn't matter."""

from tests.conftest import TEST_PASSWORD


def _register(client, email: str, phone: str = "+15550000001"):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "phone": phone,
            "full_name": "Ibrahim",
            "password": "secure123",
        },
    )


def test_register_user(client):
    response = _register(client, "new.user@example.com")

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new.user@example.com"
    assert data["full_name"] == "Ibrahim"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "password" not in data and "hashed_password" not in data


def test_register_duplicate_email(client, user):
    response = _register(client, user.email, phone="+15550000002")

    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


def test_login_success(client, user):
    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, user):
    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_unknown_email_gives_same_error_as_wrong_password(client, user):
    """Both cases must look identical, so attackers can't discover which emails exist."""
    unknown = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    wrong_password = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_protected_route_rejects_missing_and_bad_tokens(client):
    assert client.get("/api/vehicle/status").status_code in (401, 403)
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/vehicle/status", headers=bad).status_code == 401