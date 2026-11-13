"""Alerts: how they are created (door opened while armed), listed, filtered and marked read."""

import pytest

from app.models.alert import Alert, AlertCategory, AlertSeverity
from app.services import mqtt_handlers
from tests.conftest import auth_headers_for


@pytest.fixture
def make_alert(db):
    def make(vehicle, category=AlertCategory.door, is_read=False, title="Front Left Door Opened"):
        alert = Alert(
            vehicle_id=vehicle.id,
            title=title,
            description="test alert",
            category=category,
            severity=AlertSeverity.warning,
            is_read=is_read,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    return make


def test_door_opening_creates_an_alert(client, auth_headers, vehicle, broadcasts):
    mqtt_handlers.handle_mqtt_message("sensors", vehicle.device_id, {"zone_fl": False})

    data = client.get("/api/alerts/", headers=auth_headers).json()
    assert data["total"] == 1
    assert data["alerts"][0]["title"] == "Front Left Door Opened"
    assert data["alerts"][0]["category"] == "door"
    alert_messages = [msg for vid, msg in broadcasts if msg["type"] == "alert"]
    assert len(alert_messages) == 1
    assert alert_messages[0]["payload"]["title"] == "Front Left Door Opened"


def test_door_already_open_does_not_create_a_second_alert(client, auth_headers, vehicle, broadcasts):
    mqtt_handlers.handle_mqtt_message("sensors", vehicle.device_id, {"zone_fl": False})
    mqtt_handlers.handle_mqtt_message("sensors", vehicle.device_id, {"zone_fl": False})

    assert client.get("/api/alerts/", headers=auth_headers).json()["total"] == 1


def test_sensor_messages_are_ignored_while_disarmed(client, auth_headers, vehicle, db, broadcasts):
    vehicle.is_armed = False
    db.commit()

    mqtt_handlers.handle_mqtt_message("sensors", vehicle.device_id, {"zone_fl": False})

    assert client.get("/api/alerts/", headers=auth_headers).json()["total"] == 0


def test_list_alerts(client, auth_headers, vehicle, make_alert):
    make_alert(vehicle)
    make_alert(vehicle, is_read=True)

    response = client.get("/api/alerts/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["unread_count"] == 1
    assert len(data["alerts"]) == 2


def test_filter_alerts_by_category(client, auth_headers, vehicle, make_alert):
    make_alert(vehicle, category=AlertCategory.door)
    make_alert(vehicle, category=AlertCategory.engine)

    data = client.get("/api/alerts/", headers=auth_headers, params={"category": "engine"}).json()

    assert [a["category"] for a in data["alerts"]] == ["engine"]


def test_unread_alerts(client, auth_headers, vehicle, make_alert):
    unread = make_alert(vehicle)
    make_alert(vehicle, is_read=True)

    data = client.get("/api/alerts/", headers=auth_headers, params={"unread_only": True}).json()

    assert [a["id"] for a in data["alerts"]] == [unread.id]


def test_mark_single_alert_read(client, auth_headers, vehicle, make_alert):
    alert = make_alert(vehicle)

    response = client.patch(f"/api/alerts/{alert.id}/read", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == alert.id
    assert response.json()["is_read"] is True


def test_mark_all_alerts_read(client, auth_headers, vehicle, make_alert):
    make_alert(vehicle)
    make_alert(vehicle)

    response = client.patch("/api/alerts/read-all", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["marked_read"] == 2
    unread = client.get("/api/alerts/", headers=auth_headers, params={"unread_only": True}).json()
    assert unread["alerts"] == []


# ── Security: one owner can never see or change another owner's alerts ───────
def test_cannot_list_another_owners_alerts(client, vehicle, make_alert, make_user, make_vehicle):
    make_alert(vehicle)
    stranger = make_user()
    make_vehicle(stranger)

    data = client.get("/api/alerts/", headers=auth_headers_for(stranger)).json()

    assert data["total"] == 0


def test_cannot_mark_another_owners_alert_read(client, db, vehicle, make_alert, make_user, make_vehicle):
    alert = make_alert(vehicle)
    stranger = make_user()
    make_vehicle(stranger)

    response = client.patch(f"/api/alerts/{alert.id}/read", headers=auth_headers_for(stranger))

    assert response.status_code == 404
    db.refresh(alert)
    assert alert.is_read is False