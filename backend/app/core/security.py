from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt only reads the first 72 bytes of a password. passlib silently cut longer
# passwords, so every existing hash was made from the first 72 bytes. We do the same
# explicitly: newer bcrypt versions raise an error instead, which would lock out
# users with long passwords.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("ascii"))
    except ValueError:  # stored hash is malformed: treat as "wrong password", never crash
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],  # fixed list: a token can't pick its own algorithm
            options={"require": ["exp"]},  # a token with no expiry is never valid
        )
    except jwt.PyJWTError:  # bad signature, expired, malformed, missing claim...
        return None
