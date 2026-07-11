# tests/test_gps.py

def test_record_gps_reading(client, auth_headers):
    response = client.post(
        "/api/gps/",
        json={
            "latitude":  33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city":      "Islamabad",
            "address":   "F-8 Markaz, Islamabad",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["latitude"]  == 33.6844
    assert data["longitude"] == 73.0479
    assert data["speed_kmh"] == 42.5
    assert data["city"]      == "Islamabad"
    assert data["address"]   == "F-8 Markaz, Islamabad"


def test_get_latest_gps_reading(client, auth_headers):
    client.post(
        "/api/gps/",
        json={
            "latitude":  33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city":      "Islamabad",
            "address":   "F-8 Markaz, Islamabad",
        },
        headers=auth_headers,
    )
    response = client.get("/api/gps/latest", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"]  == 33.6844
    assert data["longitude"] == 73.0479
    assert data["city"]      == "Islamabad"


def test_get_gps_history(client, auth_headers):
    client.post(
        "/api/gps/",
        json={
            "latitude":  33.6844,
            "longitude": 73.0479,
            "speed_kmh": 42.5,
            "city":      "Islamabad",
            "address":   "F-8 Markaz, Islamabad",
        },
        headers=auth_headers,
    )
    response = client.get("/api/gps/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "readings" in data
    assert data["total"] >= 1
    assert len(data["readings"]) >= 1
    assert any(
        r["latitude"]  == 33.6844
        and r["longitude"] == 73.0479
        and r["city"]      == "Islamabad"
        for r in data["readings"]
    )