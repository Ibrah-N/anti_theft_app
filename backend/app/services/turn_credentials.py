# app/services/turn_credentials.py

import hmac
import hashlib
import base64
import time

from app.core.config import settings

# Matches what we hand-verified with turnutils_uclient in Step 1.
TURN_CREDENTIAL_TTL_SECONDS = 3600  # 1 hour


def generate_turn_credentials() -> dict:
    """
    Short-lived, HMAC-signed TURN credentials. coturn validates these
    independently using the same shared secret (`use-auth-secret` /
    `lt-cred-mech` in turnserver.conf) — nothing is stored server-side,
    and a leaked credential is only useful until it expires.
    """
    username   = str(int(time.time()) + TURN_CREDENTIAL_TTL_SECONDS)
    credential = base64.b64encode(
        hmac.new(
            settings.TURN_SECRET.encode(),
            username.encode(),
            hashlib.sha1,
        ).digest()
    ).decode()

    return {
        "username":   username,
        "credential": credential,
        "ttl":        TURN_CREDENTIAL_TTL_SECONDS,
        "urls": [
            f"turn:{settings.TURN_HOST}:3478",
            f"turn:{settings.TURN_HOST}:3478?transport=tcp",
            f"turns:{settings.TURN_HOST}:5349",
        ],
    }


def get_ice_servers() -> list[dict]:
    """
    Full ICE server list for the app's RTCPeerConnection config — a public
    STUN server first (lets a direct P2P path be found when possible, which
    is faster and cheaper than relaying), then our own TURN server as the
    guaranteed fallback for when direct connection isn't possible.
    """
    turn = generate_turn_credentials()
    return [
        {"urls": "stun:stun.l.google.com:19302"},
        {
            "urls":       turn["urls"],
            "username":   turn["username"],
            "credential": turn["credential"],
        },
    ]