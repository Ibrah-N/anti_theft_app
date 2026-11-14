"""Malformed input from devices and clients must be rejected cleanly, never crash.

Device messages and tokens are untrusted: they can be truncated, corrupted by a
bad network or firmware bug, or crafted by an attacker. These tests feed in
garbage and check the backend drops it and keeps working.
"""

from types import SimpleNamespace

import pytest

from app.core.security import create_access_token, create_refresh_token
from app.services import mqtt_handlers
from app.services.mqtt_service import mqtt_service


@pytest.fixture
def routed(monkeypatch):
    """Messages that get past MQTT parsing, as (type, device_id, data)."""
    calls = []
    monkeypatch.setattr(mqtt_service, "_db_callback", lambda t, d, data: calls.append((t, d, data)))
    return calls


def _deliver(topic: str, payload: bytes) -> None:
    mqtt_service._on_message(None, None, SimpleNamespace(topic=topic, payload=payload))


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff\xfe not utf-8",  # not text at all
        b"{not json",  # truncated / corrupted JSON
        b"[1, 2, 3]",  # valid JSON, but not an object
        b'"just a string"',
        b"null",
        b"",
    ],
)
def test_malformed_mqtt_payload_is_dropped_without_raising(routed, payload):
    _deliver("sg/DEV-1/status", payload)  # must not raise

    assert routed == []


def test_valid_mqtt_payload_is_routed(routed):
    _deliver("sg/DEV-1/status", b'{"battery_level": 12.5}')

    assert routed == [("status", "DEV-1", {"battery_level": 12.5})]


def test_unexpected_error_in_a_handler_does_not_escape(monkeypatch):
    def broken_handler(*args):
        raise RuntimeError("bug in handler")

    monkeypatch.setattr(mqtt_service, "_db_callback", broken_handler)

    _deliver("sg/DEV-1/status", b'{"battery_level": 12.5}')  # must not raise


def test_ack_without_a_string_cmd_is_ignored(vehicle, db, broadcasts):
    for bad in ({}, {"cmd": None}, {"cmd": ["lock"]}, {"cmd": 7}):
        mqtt_handlers.handle_mqtt_message("ack", vehicle.device_id, {**bad, "success": True})

    db.refresh(vehicle)
    assert vehicle.doors_locked is True
    assert broadcasts == []


def test_webrtc_offer_with_bad_call_id_is_dropped(vehicle, broadcasts):
    for bad in ({}, {"call_id": None}, {"call_id": ["x"]}, {"call_id": 123}):
        mqtt_handlers.handle_mqtt_message("webrtc_offer", vehicle.device_id, {**bad, "sdp": "v=0"})

    assert broadcasts == []


@pytest.mark.parametrize("sub", [None, "abc", "1; DROP TABLE users", "-1", ""])
def test_access_token_with_bad_subject_is_401(client, sub):
    claims = {} if sub is None else {"sub": sub}
    headers = {"Authorization": f"Bearer {create_access_token(claims)}"}

    assert client.get("/api/vehicle/status", headers=headers).status_code == 401


@pytest.mark.parametrize("sub", [None, "abc", ""])
def test_refresh_token_with_bad_subject_is_401(client, sub):
    claims = {} if sub is None else {"sub": sub}

    response = client.post(
        "/api/auth/refresh", json={"refresh_token": create_refresh_token(claims)}
    )

    assert response.status_code == 401
