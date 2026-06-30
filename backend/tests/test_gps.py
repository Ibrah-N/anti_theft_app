# tests/test_gps.py

def test_record_gps_reading(client):
    response = client.post(
        "/api/gps/",
        json={
            "latitude": 33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city": "Islamabad",
            "address": "F-8 Markaz, Islamabad",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["latitude"] == 33.6844
    assert data["longitude"] == 73.0479
    assert data["speed_kmh"] == 42.5
    assert data["city"] == "Islamabad"
    assert data["address"] == "F-8 Markaz, Islamabad"


def test_get_latest_gps_reading(client):
    # Create a GPS reading first
    client.post(
        "/api/gps/",
        json={
            "latitude": 33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city": "Islamabad",
            "address": "F-8 Markaz, Islamabad",
        },
    )

    response = client.get("/api/gps/latest")

    assert response.status_code == 200

    data = response.json()
    assert data["latitude"] == 33.6844
    assert data["longitude"] == 73.0479
    assert data["speed_kmh"] == 42.5
    assert data["city"] == "Islamabad"
    assert data["address"] == "F-8 Markaz, Islamabad"


def test_get_gps_history(client):
    # Create a GPS reading first
    client.post(
        "/api/gps/",
        json={
            "latitude": 33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city": "Islamabad",
            "address": "F-8 Markaz, Islamabad",
        },
    )

    response = client.get("/api/gps/history")

    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "readings" in data

    # Since the test database is shared across the test session,
    # there may already be GPS readings from previous tests.
    assert data["total"] >= 1
    assert len(data["readings"]) >= 1

    # Verify our reading exists in the history.
    assert any(
        reading["latitude"] == 33.6844
        and reading["longitude"] == 73.0479
        and reading["speed_kmh"] == 42.5
        and reading["city"] == "Islamabad"
        and reading["address"] == "F-8 Markaz, Islamabad"
        for reading in data["readings"]
    )