# tests/test_vehicle.py

def test_register_vehicle(client, auth_headers):
    response = client.post(
        "/api/vehicle/register",
        json={
            "name": "Toyota Camry 2023",
            "reg_number": "TYC-2023-0847A",
            "device_id": "ESP32-0001",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Toyota Camry 2023"
    assert data["reg_number"] == "TYC-2023-0847A"
    assert data["device_id"] == "ESP32-0001"


def test_get_vehicle_status(client, auth_headers):
    response = client.get(
        "/api/vehicle/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "engine_on" in data
    assert "fuel_flowing" in data


def test_cut_engine(client, auth_headers):
    response = client.post(
        "/api/vehicle/engine",
        json={"state": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["engine_on"] is False


def test_cut_fuel(client, auth_headers):
    response = client.post(
        "/api/vehicle/fuel",
        json={"state": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fuel_flowing"] is False