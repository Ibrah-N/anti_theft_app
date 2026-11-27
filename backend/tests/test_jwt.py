"""Token-validation rules that protect login. decode_token must return None
(never raise, never accept) for every kind of bad token."""

from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=5)


def test_valid_token_is_accepted():
    claims = decode_token(create_access_token({"sub": "1"}))
    assert claims is not None and claims["sub"] == "1"


def test_expired_token_is_rejected():
    assert decode_token(create_access_token({"sub": "1"}, timedelta(seconds=-5))) is None


def test_token_without_expiry_is_rejected():
    token = pyjwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_token(token) is None


def test_token_signed_with_another_key_is_rejected():
    token = pyjwt.encode(
        {"sub": "1", "exp": _future()},
        "a-completely-different-signing-key-0123456789",
        algorithm=settings.ALGORITHM,
    )
    assert decode_token(token) is None


def test_unsigned_alg_none_token_is_rejected():
    token = pyjwt.encode({"sub": "1", "exp": _future()}, key=None, algorithm="none")
    assert decode_token(token) is None


def test_garbage_is_rejected():
    assert decode_token("not.a.token") is None
