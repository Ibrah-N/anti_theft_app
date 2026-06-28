from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    """Ensure passwords are hashed and verified correctly."""

    password = "testpass123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_jwt_token():
    """Ensure JWT tokens are created and decoded correctly."""

    payload = {
        "sub": "user_123",
    }

    token = create_access_token(payload)

    decoded = decode_token(token)

    assert decoded is not None
    assert decoded["sub"] == "user_123"
    assert decoded["type"] == "access"
    assert "exp" in decoded