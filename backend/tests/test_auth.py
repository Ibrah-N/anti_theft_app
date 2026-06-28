# tests/test_auth.py

def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "ibrahim@smartguard.com",
            "phone": "+1234567890",
            "full_name": "Ibrahim",
            "password": "secure123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ibrahim@smartguard.com"
    assert data["full_name"] == "Ibrahim"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data

def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "ibrahim@smartguard.com",
            "password": "secure123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_register_duplicate_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "ibrahim@smartguard.com",
            "phone": "+1111111111",
            "full_name": "Duplicate User",
            "password": "secure123",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert "already" in data["detail"].lower()

def test_login_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "ibrahim@smartguard.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "invalid" in data["detail"].lower()