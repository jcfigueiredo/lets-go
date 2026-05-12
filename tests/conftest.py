"""Shared pytest fixtures.

This file is intentionally minimal at this stage. Task 7 will add a
SAVEPOINT-isolated `db` session fixture; for now, this file owns the
environment-variable hygiene fixture that prevents stale exports from
shadowing default settings tests.
"""

import pytest


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
