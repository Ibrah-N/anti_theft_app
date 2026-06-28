from sqlalchemy import text

from tests.conftest import test_engine


def test_database_connection():
    """Ensure the test database is reachable."""

    with test_engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )

        database_name = result.scalar()

    assert database_name == "smartguard_test"