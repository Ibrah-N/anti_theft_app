# app/core/device_auth.py
#
# Authentication for the camera/firmware (NOT for the phone app).
#
# The app logs in with a user JWT. The camera can't do that — it has no user —
# so each vehicle gets a long random "device key". The firmware sends it on
# every request:
#
#     X-Device-Id:  esp-001
#     X-Device-Key: vgx_....
#
# Only a SHA-256 hash of the key is stored in the database. The key itself is
# 256 bits of randomness, so a plain fast hash is fine here (unlike passwords,
# there is nothing to brute-force).

import hashlib
import hmac
import logging
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vehicle import Vehicle

logger = logging.getLogger(__name__)

KEY_PREFIX = "vgx_"


def generate_device_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_device_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _unauthorized(detail: str = "Invalid device credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "DeviceKey"},
    )


def get_device_vehicle(
    x_device_id: str | None  = Header(default=None),
    x_device_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Vehicle:
    """Resolve the vehicle for a camera request, or raise 401."""
    if not x_device_id or not x_device_key:
        raise _unauthorized("Missing X-Device-Id or X-Device-Key header")

    vehicle = db.query(Vehicle).filter(Vehicle.device_id == x_device_id).first()

    # Always compute and compare a hash, even for an unknown device, so the
    # response time doesn't reveal which device IDs exist.
    presented = hash_device_key(x_device_key)
    stored    = vehicle.device_key_hash if vehicle and vehicle.device_key_hash else "0" * 64

    if not hmac.compare_digest(presented, stored) or vehicle is None or not vehicle.device_key_hash:
        logger.warning(f"Device auth failed for device_id={x_device_id!r}")
        raise _unauthorized()

    return vehicle