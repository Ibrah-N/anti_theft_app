"""Vehicle registration, status and remote commands.

Commands are two-phase: the API publishes an MQTT command and returns right away;
the vehicle's state changes only when the DEVICE reports it. Engine and fuel are
confirmed by the device's next `status` message; lock/arm/start/ac/mirrors by an
`ack` message. These tests check both halves.
"""

import pytest

from app.models.vehicle import Vehicle
from app.services import mqtt_handlers
from tests.conftest import auth_headers_for


def test_register_vehicle(client, user):
    response = client.post(
        "/api/vehicle/register",
        json={
            "name": "Toyota Camry 2023",
            "reg_number": "TYC-2023-0847A",
            "device_id": "ESP32-0001",
        },
        headers=auth_headers_for(user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Toyota Camry 2023"
    assert data["reg_number"] == "TYC-2023-0847A"
    assert data["device_id"] == "ESP32-0001"


def test_register_vehicle_rejects_device_already_registered(client, make_user, vehicle):
    other_user = make_user()

    response = client.post(
        "/api/vehicle/register",
        json={"name": "Copycat", "reg_number": "COPY-1", "device_id": vehicle.device_id},
        headers=auth_headers_for(other_user),
    )

    assert response.status_code == 400


def test_get_vehicle_status(client, auth_headers, vehicle):
    response = client.get("/api/vehicle/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == vehicle.id
    assert data["engine_on"] is False
    assert data["fuel_flowing"] is True


def test_status_without_a_vehicle_is_404(client, user):
    response = client.get("/api/vehicle/status", headers=auth_headers_for(user))

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("endpoint", "topic_suffix"),
    [("/api/vehicle/engine", "cmd/engine"), ("/api/vehicle/fuel", "cmd/fuel")],
)
def test_command_is_published_to_the_vehicles_device(
    client, auth_headers, vehicle, mqtt, endpoint, topic_suffix
):
    response = client.post(endpoint, json={"state": False}, headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["state"] is False
    assert mqtt.topics() == [f"sg/{vehicle.device_id}/{topic_suffix}"]
    assert mqtt.published[0][1]["state"] is False


def test_engine_state_changes_only_after_device_confirms(
    client, auth_headers, vehicle, mqtt, db, broadcasts
):
    client.post("/api/vehicle/engine", json={"state": True}, headers=auth_headers)

    # The command alone must not change the stored state.
    assert client.get("/api/vehicle/status", headers=auth_headers).json()["engine_on"] is False

    # The device reports the engine is on.
    mqtt_handlers.handle_mqtt_message("status", vehicle.device_id, {"engine_on": True})

    assert client.get("/api/vehicle/status", headers=auth_headers).json()["engine_on"] is True


def test_lock_state_changes_only_on_successful_ack(
    client, auth_headers, vehicle, mqtt, db, broadcasts
):
    client.post("/api/vehicle/lock", json={"state": False}, headers=auth_headers)

    mqtt_handlers.handle_mqtt_message(
        "ack", vehicle.device_id, {"cmd": "lock", "state": False, "success": False}
    )
    db.expire_all()
    assert db.get(Vehicle, vehicle.id).doors_locked is True, "a failed ack must not change state"

    mqtt_handlers.handle_mqtt_message(
        "ack", vehicle.device_id, {"cmd": "lock", "state": False, "success": True}
    )
    db.expire_all()
    assert db.get(Vehicle, vehicle.id).doors_locked is False


def test_command_when_broker_is_down_is_503(client, auth_headers):
    # No `mqtt` fixture: the backend is not connected to a broker.
    response = client.post("/api/vehicle/engine", json={"state": False}, headers=auth_headers)

    assert response.status_code == 503


def test_command_when_disarmed_is_409_and_nothing_is_sent(client, auth_headers, vehicle, mqtt, db):
    vehicle.is_armed = False
    db.commit()

    response = client.post("/api/vehicle/engine", json={"state": False}, headers=auth_headers)

    assert response.status_code == 409
    assert mqtt.published == []


def test_command_requires_login(client, mqtt):
    response = client.post("/api/vehicle/engine", json={"state": False})

    assert response.status_code in (401, 403)
    assert mqtt.published == []
