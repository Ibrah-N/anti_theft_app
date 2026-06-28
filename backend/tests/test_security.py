from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_password_hashing():
    """Ensure passwords are hashed and verified correctly."""

    password = "testpass123"

    hashed_password = hash_password(password)

    # The hash should not be the same as the original password
    assert hashed_password != password

    # Correct password should verify successfully
    assert verify_password(password, hashed_password)

    # Incorrect password should fail verification
    assert not verify_password("wrongpassword", hashed_password)


def test_jwt_token():
    """Ensure JWT tokens are created and decoded correctly."""

    payload = {"sub": "user_123"}

    token = create_access_token(payload)
    decoded_payload = decode_token(token)

    assert decoded_payload is not None
    assert decoded_payload["sub"] == "user_123"