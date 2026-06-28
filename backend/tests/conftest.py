# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "postgresql+psycopg2://smartguard_user:smartguard_pass@localhost:5432/smartguard_test"

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

from app.core.database import Base, get_db
from app.models import User, Vehicle, Alert  # noqa: F401

Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)

from app.main import app  # noqa: E402

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(scope="session")
def auth_headers(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "alerts_user@smartguard.com",
            "phone": "+9999999999",
            "full_name": "Alerts User",
            "password": "secure123",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={
            "email": "alerts_user@smartguard.com",
            "password": "secure123",
        },
    )
    token = response.json()["access_token"]

    client.post(
        "/api/vehicle/register",
        json={
            "name": "Test Vehicle",
            "reg_number": "TEST-001",
            "device_id": "ESP32-TEST",
        },
    )

    return {"Authorization": f"Bearer {token}"}