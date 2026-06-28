from sqlalchemy import text

from app.core.database import engine
from app.core.config import settings


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )

        database_name = result.scalar()

    expected = settings.DATABASE_URL.rsplit("/", 1)[-1]

    assert database_name == expected