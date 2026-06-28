# tests/test_alerts.py


def create_test_alerts(client, auth_headers):
    """Trigger engine and fuel cutoff to generate alerts."""
    client.post("/api/vehicle/engine", json={"state": False})
    client.post("/api/vehicle/fuel", json={"state": False})


def test_list_alerts(client, auth_headers):
    create_test_alerts(client, auth_headers)

    response = client.get("/api/alerts/", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "alerts" in data
    assert "total" in data
    assert "unread_count" in data
    assert isinstance(data["alerts"], list)
    assert data["total"] >= 2


def test_filter_alerts_by_category(client, auth_headers):
    response = client.get("/api/alerts/", headers=auth_headers, params={"category": "engine"})
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["alerts"], list)
    for alert in data["alerts"]:
        assert alert["category"] == "engine"


def test_unread_alerts(client, auth_headers):
    response = client.get("/api/alerts/", headers=auth_headers, params={"unread_only": True})
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["alerts"], list)
    for alert in data["alerts"]:
        assert alert["is_read"] is False


def test_mark_single_alert_read(client, auth_headers):
    alerts_data = client.get("/api/alerts/", headers=auth_headers).json()
    assert len(alerts_data["alerts"]) > 0

    alert_id = alerts_data["alerts"][0]["id"]
    response = client.patch(f"/api/alerts/{alert_id}/read")
    assert response.status_code == 200

    data = response.json()
    assert data["is_read"] is True
    assert data["id"] == alert_id


def test_mark_all_alerts_read(client, auth_headers):
    response = client.patch("/api/alerts/read-all")
    assert response.status_code == 200
    assert "marked_read" in response.json()

    # Verify no unread alerts remain
    response = client.get("/api/alerts/", headers=auth_headers, params={"unread_only": True})
    assert response.status_code == 200
    data = response.json()
    assert data["alerts"] == []
    assert data["unread_count"] == 0