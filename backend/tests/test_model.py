from sqlalchemy import inspect

from app.core.database import Base, engine

# Import all models so SQLAlchemy registers them with Base.metadata
from app.models import User, Vehicle, Alert


def test_database_tables_created():
    """Ensure all database tables are created successfully."""

    # Create all tables (safe to call multiple times)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = {
        "users",
        "vehicles",
        "alerts",
    }

    # Verify every expected table exists
    for table in expected_tables:
        assert table in tables, f"Table '{table}' was not created."