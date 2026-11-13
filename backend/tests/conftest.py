"""Test configuration shared by every test module.

How the test environment works:

1. Settings are forced to test values BEFORE any app module is imported.
   `app.core.config.settings` is created at import time, so this must run first.
   Values are assigned (not `setdefault`) so a developer's own `.env` can never
   point the tests at a real database or broker.
2. A safety guard refuses to run unless the database name contains "test".
   The schema reset below drops everything in that database.
3. The schema is built by running the real Alembic migrations, exactly as on the
   server. A broken migration therefore fails the test run instead of a deploy.

Start the services first:  docker compose -f docker-compose.test.yml up -d --wait
Point at other services with the TEST_DATABASE_URL / TEST_MQTT_HOST / TEST_MQTT_PORT
environment variables (CI does this).
"""

import os
import tempfile
from pathlib import Path

# ── 1. Force test settings before importing the app ──────────────────────────
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://vigilx_test:vigilx_test@localhost:5433/vigilx_test",
)
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="vigilx-test-media-")

os.environ.update(
    {
        "VIGILX_ENV_FILE": "",  # read no .env file at all (see app/core/config.py)
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "test-secret-key-not-for-production",
        "DEBUG": "False",
        "MQTT_HOST": os.environ.get("TEST_MQTT_HOST", "localhost"),
        "MQTT_PORT": os.environ.get("TEST_MQTT_PORT", "1884"),
        "MQTT_USERNAME": "test",
        "MQTT_PASSWORD": "test",
        "MQTT_CLIENT_ID": "vigilx_backend_test",
        "TURN_SECRET": "test-turn-secret",
        "TURN_HOST": "turn.test.invalid",
        "MEDIA_ROOT": TEST_MEDIA_ROOT,
    }
)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# ── 2. Safety guard ───────────────────────────────────────────────────────────
_db_name = make_url(TEST_DATABASE_URL).database or ""
if "test" not in _db_name.lower():
    raise RuntimeError(
        f"Refusing to run tests against database {_db_name!r}: the test suite "
        "wipes its database. Use a database whose name contains 'test'."
    )

BACKEND_DIR = Path(__file__).resolve().parents[1]

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


def _reset_schema() -> None:
    """Drop every object in the test database, then migrate it to head."""
    with test_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    # Config() without an ini file: alembic/env.py then skips fileConfig(), which
    # would otherwise reconfigure logging and silence the app's loggers in tests.
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    _reset_schema()
    yield
    test_engine.dispose()


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
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/vehicle/register",
        json={
            "name": "Test Vehicle",
            "reg_number": "TEST-001",
            "device_id": "ESP32-TEST",
        },
        headers=headers,
    )

    return headers