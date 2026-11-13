"""Camera-state reports over MQTT, the finalize-recording hint on stream start,
and routing of the camera/state topic."""

import json
from types import SimpleNamespace

import pytest

from app.services import camera_state, mqtt_handlers
from app.services.mqtt_service import mqtt_service


@pytest.fixture(autouse=True)
def _clear_camera_state(vehicle):
    """camera_state lives in memory, not in the database, so reset it per test."""
    camera_state.clear(vehicle.id)
    yield
    camera_state.clear(vehicle.id)


def _camera_messages(broadcasts):
    return [msg["payload"] for _, msg in broadcasts if msg["type"] == "camera_state"]


def test_camera_state_is_stored_and_forwarded(client, auth_headers, vehicle, broadcasts):
    mqtt_handlers.handle_mqtt_message(
        "camera_state",
        vehicle.device_id,
        {
            "state": "recording",
            "clip_id": "evt-0001-abcd",
            "reason": "door_opened",
            "elapsed_s": 42.5,
            "junk": "ignored",
        },
    )

    forwarded = _camera_messages(broadcasts)
    assert len(forwarded) == 1
    assert forwarded[0]["state"] == "recording"
    assert forwarded[0]["reason"] == "door_opened"
    assert "junk" not in forwarded[0], "unknown fields must not be passed to the app"

    stored = client.get("/api/vehicle/camera/state", headers=auth_headers).json()
    assert stored["camera"]["state"] == "recording"
    assert stored["camera"]["clip_id"] == "evt-0001-abcd"


def test_invalid_camera_state_is_ignored(client, auth_headers, vehicle, broadcasts):
    mqtt_handlers.handle_mqtt_message("camera_state", vehicle.device_id, {"state": "exploding"})
    mqtt_handlers.handle_mqtt_message("camera_state", vehicle.device_id, {})

    assert _camera_messages(broadcasts) == []
    assert client.get("/api/vehicle/camera/state", headers=auth_headers).json() == {"camera": None}


def test_camera_state_not_dropped_when_disarmed(vehicle, db, broadcasts):
    # sensors/gps messages are dropped while disarmed; camera state must not be.
    vehicle.is_armed = False
    db.commit()

    mqtt_handlers.handle_mqtt_message("camera_state", vehicle.device_id, {"state": "idle"})

    assert [m["state"] for m in _camera_messages(broadcasts)] == ["idle"]


def test_mqtt_topic_routes_to_camera_state(monkeypatch):
    calls = []
    monkeypatch.setattr(mqtt_service, "_db_callback", lambda t, d, data: calls.append((t, d, data)))
    message = SimpleNamespace(
        topic="sg/ESP32-TEST/camera/state",
        payload=json.dumps({"state": "uploading"}).encode(),
    )

    mqtt_service._on_message(None, None, message)

    assert calls == [("camera_state", "ESP32-TEST", {"state": "uploading"})]


def test_stream_start_tells_camera_to_finalize_recording(client, auth_headers, mqtt):
    response = client.post("/api/vehicle/camera/start", headers=auth_headers)

    assert response.status_code == 200, response.text
    topic, body = mqtt.published[0]
    assert topic.endswith("/cmd/camera/start")
    assert body["finalize_recording"] is True
    assert body["call_id"] == response.json()["call_id"]