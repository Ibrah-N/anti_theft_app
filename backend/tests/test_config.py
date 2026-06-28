from app.core.config import settings


def test_database_url_exists():
    """Ensure the database URL is loaded from the configuration."""

    assert settings.DATABASE_URL is not None
    assert settings.DATABASE_URL != ""
    assert settings.DATABASE_URL.startswith("postgresql")