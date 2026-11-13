from sqlalchemy import inspect

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core.database import Base
from tests.conftest import test_engine


def test_migrations_create_every_model_table():
    """Running the Alembic migrations creates a table for every SQLAlchemy model.

    The schema in the test database comes only from the migrations (see conftest).
    If someone adds a model but forgets its migration, this test fails.
    """
    tables_in_db = set(inspect(test_engine).get_table_names())
    tables_in_models = set(Base.metadata.tables)

    missing = tables_in_models - tables_in_db
    assert not missing, f"Models without a migration: {sorted(missing)}"
