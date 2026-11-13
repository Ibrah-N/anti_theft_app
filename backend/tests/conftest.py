"""Test configuration shared by every test module.

How the test environment works:

1. Settings are forced to test values BEFORE any app module is imported.
   `app.core.config.settings` is created at import time, so this must run first.
   VIGILX_ENV_FILE="" makes the app read no .env file at all.
2. A safety guard refuses to run unless the database name contains "test".
   The schema reset below drops everything in that database.
3. The schema is built once per run by the real Alembic migrations.
4. Every test runs inside a database transaction that is rolled back afterwards,
   so tests never see each other's data and can run in any order.
5. Nothing talks to the network unless a test asks for it: MQTT publishes are
   captured by the `mqtt` fixture, WebSocket broadcasts by `broadcasts`.

Start the services first:  docker compose -f docker-compose.test.yml up -d --wait
Point at other services with TEST_DATABASE_URL / TEST_MQTT_HOST / TEST_MQTT_PORT.
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

import asyncio  # noqa: E402
import itertools  # noqa: E402
import json  # noqa: E402
from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# ── 2. Safety guard ───────────────────────────────────────────────────────────
_db_name = make_url(TEST_DATABASE_URL).database or ""
if "test" not in _db_name.lower():
    raise RuntimeError(
        f"Refusing to run tests against database {_db_name!r}: the test suite "
        "wipes its database. Use a database whose name contains 'test'."
    )

BACKEND_DIR = Path(__file__).resolve().parents[1]
test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

from app.core import database  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vehicle import Vehicle  # noqa: E402
from app.routes import ws as ws_routes  # noqa: E402
from app.services import clip_storage, media_cleanup, mqtt_handlers  # noqa: E402
from app.services.mqtt_service import mqtt_service  # noqa: E402

# Modules that open their own sessions with `SessionLocal()` instead of using the
# request's session. Each one is pointed at the test transaction (see below).
_MODULES_WITH_SESSIONLOCAL = (database, mqtt_handlers, clip_storage, media_cleanup, ws_routes)

TEST_PASSWORD = "secure-test-password"
# bcrypt is deliberately slow (~0.25 s). Hash once and reuse it for every user.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)
_unique = itertools.count(1)


# ── 3. Schema: built once per run by the real migrations ─────────────────────
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


@pytest.fixture(scope="session", autouse=True)
def _database_schema() -> Iterator[None]:
    _reset_schema()
    yield
    test_engine.dispose()


# ── 4. One rolled-back transaction per test ──────────────────────────────────
@pytest.fixture
def db_connection() -> Iterator[Any]:
    """A connection with an open transaction that is rolled back after the test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def session_factory(db_connection) -> Callable[[], Session]:
    """Makes sessions that share the test transaction.

    join_transaction_mode="create_savepoint": when app code calls
    session.commit(), only a SAVEPOINT is released. The outer transaction
    stays open, so the rollback at the end of the test still undoes everything.
    """

    def make() -> Session:
        return Session(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
        )

    return make


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    """A session for the test itself: create rows, then check results."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _all_sessions_use_test_transaction(session_factory, monkeypatch) -> Iterator[None]:
    """Route EVERY database session in the app to the test transaction.

    autouse=True: applied to every test automatically, so no test can reach the
    database through the app's real SessionLocal (which would not see the test's
    data, and whose writes would not be rolled back).
    """

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    for module in _MODULES_WITH_SESSIONLOCAL:
        monkeypatch.setattr(module, "SessionLocal", session_factory)
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client() -> TestClient:
    """HTTP client for the app.

    The app's startup hooks (Firebase, MQTT connection, cleanup thread) do NOT run:
    TestClient only runs them when used as a context manager.
    """
    return TestClient(app)


# ── Factories: create test data directly in the database ─────────────────────
@pytest.fixture
def make_user(db) -> Callable[..., User]:
    def make(**overrides: Any) -> User:
        n = next(_unique)
        values: dict[str, Any] = {
            "email": f"user{n}@example.com",
            "phone": f"+1000000{n:04d}",
            "full_name": f"Test User {n}",
            "hashed_password": _TEST_PASSWORD_HASH,
            "is_active": True,
        }
        values.update(overrides)
        user = User(**values)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return make


@pytest.fixture
def make_vehicle(db) -> Callable[..., Vehicle]:
    def make(owner: User, **overrides: Any) -> Vehicle:
        n = next(_unique)
        values: dict[str, Any] = {
            "owner_id": owner.id,
            "name": f"Test Vehicle {n}",
            "reg_number": f"TEST-{n:04d}",
            "device_id": f"TEST-DEVICE-{n:04d}",
        }
        values.update(overrides)
        vehicle = Vehicle(**values)
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    return make


def auth_headers_for(user: User) -> dict[str, str]:
    """Bearer headers for a user, without going through the login endpoint."""
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(make_user) -> User:
    return make_user()


@pytest.fixture
def vehicle(make_vehicle, user) -> Vehicle:
    return make_vehicle(user)


@pytest.fixture
def auth_headers(user, vehicle) -> dict[str, str]:
    """Headers for a user who owns one vehicle (the `vehicle` fixture)."""
    return auth_headers_for(user)


# ── 5. Fakes for MQTT and WebSocket ──────────────────────────────────────────
@dataclass
class FakeMqtt:
    """Records what the backend publishes instead of sending it to a broker."""

    published: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> Any:
        self.published.append((topic, json.loads(payload)))
        return _PublishResult()

    def topics(self) -> list[str]:
        return [topic for topic, _ in self.published]


class _PublishResult:
    rc = 0
    mid = 1


@pytest.fixture
def mqtt(monkeypatch) -> FakeMqtt:
    """Pretend the broker is connected and capture every publish."""
    fake = FakeMqtt()
    monkeypatch.setattr(mqtt_service, "_connected", True)
    monkeypatch.setattr(mqtt_service.client, "publish", fake.publish)
    return fake


@pytest.fixture
def broadcasts(monkeypatch) -> list[tuple[int, dict[str, Any]]]:
    """Capture WebSocket broadcasts as (vehicle_id, message), run immediately."""
    captured: list[tuple[int, dict[str, Any]]] = []

    async def fake_broadcast(vehicle_id: int, message: dict[str, Any]) -> None:
        captured.append((vehicle_id, message))

    monkeypatch.setattr(mqtt_handlers.ws_manager, "broadcast", fake_broadcast)
    monkeypatch.setattr(mqtt_handlers, "_broadcast_threadsafe", asyncio.run)
    return captured