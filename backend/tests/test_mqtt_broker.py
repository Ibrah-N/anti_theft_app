"""Integration test against the real Mosquitto broker from docker-compose.test.yml.

Every other test fakes MQTT. This one proves the real path works: the backend's
MQTT service connects, its commands reach a device subscribed on the broker, and
device messages published on the broker reach the backend's handler.
"""

import json
import queue
import uuid

import paho.mqtt.client as paho
import pytest

from app.core.config import settings
from app.services.mqtt_service import MQTTService

TIMEOUT_S = 5.0


@pytest.fixture
def backend_mqtt(monkeypatch):
    """A fresh, connected MQTTService (not the app's global one)."""
    monkeypatch.setattr(settings, "MQTT_CLIENT_ID", f"backend-test-{uuid.uuid4().hex[:8]}")
    service = MQTTService()
    received: queue.Queue = queue.Queue()
    service.set_db_callback(lambda msg_type, device_id, data: received.put((msg_type, device_id, data)))

    # The backend subscribes to 7 topics on connect. Wait until the broker has
    # confirmed all of them; otherwise a device message sent right away could
    # arrive before the subscription exists and be lost (a flaky test).
    subacks: queue.Queue = queue.Queue()
    service.client.on_subscribe = lambda *args: subacks.put(True)
    not_running = (
        f"Test MQTT broker not reachable at {settings.MQTT_HOST}:{settings.MQTT_PORT}. "
        "Start it with: docker compose -f docker-compose.test.yml up -d --wait"
    )
    try:
        service.connect()
    except OSError:
        pytest.fail(not_running)
    try:
        for _ in range(7):
            subacks.get(timeout=TIMEOUT_S)
    except queue.Empty:
        service.disconnect()
        pytest.fail(not_running)
    assert service.is_connected
    yield service, received
    service.disconnect()


@pytest.fixture
def fake_device():
    """A plain MQTT client playing the device's role."""
    device_id = f"BROKER-TEST-{uuid.uuid4().hex[:8]}"
    client = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id=device_id)
    inbox: queue.Queue = queue.Queue()
    subscribed = queue.Queue()
    client.on_message = lambda c, u, msg: inbox.put((msg.topic, json.loads(msg.payload)))
    client.on_subscribe = lambda *args: subscribed.put(True)
    client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=30)
    client.loop_start()
    client.subscribe(f"sg/{device_id}/cmd/#", qos=1)
    subscribed.get(timeout=TIMEOUT_S)
    yield device_id, client, inbox
    client.loop_stop()
    client.disconnect()


def test_backend_command_reaches_the_device(backend_mqtt, fake_device):
    service, _ = backend_mqtt
    device_id, _, inbox = fake_device

    service.publish_engine_command(device_id, False)

    topic, body = inbox.get(timeout=TIMEOUT_S)
    assert topic == f"sg/{device_id}/cmd/engine"
    assert body["state"] is False


def test_device_status_reaches_the_backend(backend_mqtt, fake_device):
    _, received = backend_mqtt
    device_id, device_client, _ = fake_device

    device_client.publish(f"sg/{device_id}/status", json.dumps({"battery_level": 12.4}), qos=1)

    msg_type, sender, data = received.get(timeout=TIMEOUT_S)
    assert (msg_type, sender) == ("status", device_id)
    assert data == {"battery_level": 12.4}