from sqlalchemy import inspect

from app.core.database import Base
from app.models import User, Vehicle, Alert

from tests.conftest import test_engine


def test_database_tables_created():
    """Ensure all model tables exist in the test database."""

    Base.metadata.create_all(bind=test_engine)

    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())

    expected_tables = {
        User.__tablename__,
        Vehicle.__tablename__,
        Alert.__tablename__,
    }

    assert expected_tables.issubset(tables)