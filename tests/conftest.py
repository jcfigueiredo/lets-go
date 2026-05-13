"""Shared pytest fixtures.

This module owns:

- ``_isolate_settings_env`` (autouse) — strips settings env vars before
  every test, so stale shell exports never shadow defaults.
- ``test_engine`` (session) — a SQLAlchemy engine bound to
  ``TEST_DATABASE_URL`` for tests that need a real connection.
- ``db`` (per-test) — a ``Session`` wrapped in an outer transaction and
  a SAVEPOINT, providing rollback isolation between tests.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine, event
from sqlmodel import Session

from lab.config import get_settings


@pytest.fixture(autouse=True)
def _isolate_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove settings-related env vars before each test.

    Without this, a developer who has `source`-d the project's .env in
    their shell (or a CI job with these vars exported) would see tests
    pass or fail against the exported values rather than the Settings
    defaults. Autouse keeps this invisible at the call site.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """Session-scoped engine bound to TEST_DATABASE_URL."""
    engine = create_engine(get_settings().TEST_DATABASE_URL, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(test_engine: Engine) -> Iterator[Session]:
    """Per-test session with SAVEPOINT-based rollback isolation.

    Each test runs inside an outer transaction. A SAVEPOINT is opened so
    that ``session.commit()`` inside the test commits the savepoint (not
    the outer transaction); the outer transaction is always rolled back
    at teardown, so the database is unchanged between tests.
    """
    connection: Connection = test_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction) -> None:
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if outer.is_active:
            outer.rollback()
        connection.close()


@pytest.fixture
def factories(db: Session):
    """Bind every registered factory to the per-test session and return a namespace.

    Tests use ``factories.researcher()``, ``factories.project()``, etc.
    """
    from tests.factories import ALL_FACTORIES, factory_namespace

    for cls in ALL_FACTORIES:
        cls._meta.sqlalchemy_session = db

    return factory_namespace()
