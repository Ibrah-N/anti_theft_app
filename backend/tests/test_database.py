from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.conftest import TEST_DATABASE_URL, test_engine


def test_database_connection():
    """The test database is reachable and is the one the suite was configured for."""
    with test_engine.connect() as connection:
        database_name = connection.execute(text("SELECT current_database()")).scalar()

    assert database_name == make_url(TEST_DATABASE_URL).database
