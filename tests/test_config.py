import pytest

from lab.config import Settings


def test_default_database_url():
    s = Settings(_env_file=None)

    assert s.DATABASE_URL == "postgresql+psycopg://postgres:postgres@localhost:5432/lab"


def test_default_test_database_url():
    s = Settings(_env_file=None)

    assert s.TEST_DATABASE_URL == "postgresql+psycopg://postgres:postgres@localhost:5432/lab_test"


def test_database_url_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/x")

    s = Settings(_env_file=None)

    assert s.DATABASE_URL == "postgresql+psycopg://u:p@h:5432/x"


def test_normalize_postgresql_prefix_to_psycopg():
    s = Settings(_env_file=None, DATABASE_URL="postgresql://u:p@h:5432/x")

    assert s.DATABASE_URL == "postgresql+psycopg://u:p@h:5432/x"


def test_normalize_leaves_already_psycopg_unchanged():
    s = Settings(_env_file=None, DATABASE_URL="postgresql+psycopg://u:p@h:5432/x")

    assert s.DATABASE_URL == "postgresql+psycopg://u:p@h:5432/x"
