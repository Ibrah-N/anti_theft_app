# tests/test_camera_state.py
#
# Step 3: camera-state reports over MQTT, the stop-recording hint on stream
# start, and the clip_ready notification.

import json
from types import SimpleNamespace

import pytest

import conftest
from app.services import camera_state, mqtt_handlers
from app.services.mqtt_service import mqtt_service


@pytest.fixture()
def sent(monkeypatch):
    """Capture WebSocket broadcasts instead of needing a running event loop."""
    captured = []
    async def fake_broadcast_event(vehicle_id, msg_type, payload):
        captured.append((vehicle_id, msg_type, payload))
    def run_now(coro):
        import asyncio
        asyncio.run(coro)
    monkeypatch.setattr(mqtt_handlers, "_broadcast_event", fake_broadcast_event)
    monkeypatch.setattr(mqtt_handlers, "_broadcast_threadsafe", run_now)
    monkeypatch.setattr(mqtt_handlers, "SessionLocal", conftest.TestSessionLocal)
    return captured


def _vehicle_id(client, auth_headers):
    return client.get("/api/vehicle/status", headers=auth_headers).json()["id"]


def test_camera_state_is_stored_and_forwarded(client, auth_headers, sent):
    vid = _vehicle_id(client, auth_headers)
    camera_state.clear(vid)
    mqtt_handlers.handle_mqtt_message("camera_state", "ESP32-TEST", {
        "state": "recording", "clip_id": "evt-0001-abcd", "reason": "door_opened",
        "elapsed_s": 42.5, "junk": "ignored",
    })
    assert sent and sent[0][1] == "camera_state"
    payload = sent[0][2]
    assert payload["state"] == "recording" and payload["reason"] == "door_opened"
    assert "junk" not in payload

    r = client.get("/api/vehicle/camera/state", headers=auth_headers).json()
    assert r["camera"]["state"] == "recording" and r["camera"]["clip_id"] == "evt-0001-abcd"


def test_invalid_camera_state_is_ignored(client, auth_headers, sent):
    vid = _vehicle_id(client, auth_headers)
    camera_state.clear(vid)
    mqtt_handlers.handle_mqtt_message("camera_state", "ESP32-TEST", {"state": "exploding"})
    mqtt_handlers.handle_mqtt_message("camera_state", "ESP32-TEST", {})
    assert sent == []
    assert client.get("/api/vehicle/camera/state", headers=auth_headers).json() == {"camera": None}


def test_camera_state_not_dropped_when_disarmed(client, auth_headers, sent):
    # sensors/gps are dropped while disarmed; camera state must not be.
    client.post("/api/vehicle/arm", json={"state": False}, headers=auth_headers)
    mqtt_handlers.handle_mqtt_message("camera_state", "ESP32-TEST", {"state": "idle"})
    assert sent and sent[0][2]["state"] == "idle"


def test_mqtt_topic_routes_to_camera_state(monkeypatch):
    calls = []
    monkeypatch.setattr(mqtt_service, "_db_callback", lambda t, d, data: calls.append((t, d, data)))
    msg = SimpleNamespace(topic="sg/ESP32-TEST/camera/state",
                          payload=json.dumps({"state": "uploading"}).encode())
    mqtt_service._on_message(None, None, msg)
    assert calls == [("camera_state", "ESP32-TEST", {"state": "uploading"})]


def test_stream_start_tells_camera_to_finalize_recording(client, auth_headers, monkeypatch):
    published = []
    monkeypatch.setattr(mqtt_service, "_connected", True)
    monkeypatch.setattr(mqtt_service.client, "publish",
                        lambda topic, payload, **kw: published.append((topic, json.loads(payload))))
    r = client.post("/api/vehicle/camera/start", headers=auth_headers)
    assert r.status_code == 200, r.text
    topic, body = published[0]
    assert topic.endswith("/cmd/camera/start")
    assert body["finalize_recording"] is True and body["call_id"] == r.json()["call_id"]