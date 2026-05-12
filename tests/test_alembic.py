from sqlalchemy import create_engine, inspect

from lab.config import get_settings


def test_alembic_version_table_exists_after_migrate():
    """`make migrate-test` (run as a test dependency) must create alembic_version."""
    test_engine = create_engine(get_settings().TEST_DATABASE_URL, future=True)
    try:
        inspector = inspect(test_engine)
        assert "alembic_version" in inspector.get_table_names()
    finally:
        test_engine.dispose()
