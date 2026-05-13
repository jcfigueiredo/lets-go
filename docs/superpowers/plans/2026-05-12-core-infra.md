# Core Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the project's core infrastructure — Postgres in docker-compose, SQLModel + SQLAlchemy 2.x (sync) + Alembic wiring, pytest with 100% branch coverage enforced from commit #1, and a self-documenting Makefile — with **no domain models**. The schema design lands in a follow-up plan.

**Architecture:** Sync SQLAlchemy/SQLModel on `psycopg[binary]` against a single Postgres container hosting two databases (`lab`, `lab_test`). Alembic generates migrations from `lab.models` (currently empty). Tests run on the host against `lab_test`; each test wraps an outer transaction with a SAVEPOINT-based pattern so inner commits don't leak. Coverage gate (`--cov-branch --cov-fail-under=100`) lives in `pyproject.toml` and is enforced by every `pytest` invocation.

**Tech Stack:** Python 3.11+, `uv`, SQLModel, SQLAlchemy 2.x, Alembic, `psycopg[binary]>=3.2`, `pydantic-settings`, `pytest`, `pytest-cov`, `pytest-spec`, `ruff`, Docker Compose, Postgres 16, Make.

**Reference:** [Spec — Core Infrastructure Design](../specs/2026-05-12-core-infra-design.md)

---

## Conventions used in this plan

- `$REPO` = `/Users/claudio/projects/csouza/lets-go`. All paths relative to it.
- `uv run <cmd>` is how Python tools are invoked. Equivalently, `make <target>` once the Makefile exists.
- After each task, the suite must be green at 100% branch coverage. Each task's last steps verify this.
- Commits use Conventional Commits (`feat:`, `chore:`, `test:`, etc.). Co-author line omitted from samples; add it if your `commit` skill expects it.

---

## Task 1: Project skeleton with the coverage gate already on

**Files:**
- Create: `.gitignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `src/lab/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_canary.py`
- Create: `Makefile`
- Create: `.env.example`

- [ ] **Step 1: Initialize git** (only if not already a repo)

```bash
cd /Users/claudio/projects/csouza/lets-go
git init
git add lab-experiment-tracking-system.txt CLAUDE.md docs/
git commit -m "chore: initial commit with spec and design docs"
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
*.egg-info/
.env
.python-version-cache
```

- [ ] **Step 3: Write `.python-version`**

```
3.13
```

- [ ] **Step 4: Write `pyproject.toml`**

```toml
[project]
name = "lab"
version = "0.1.0"
description = "Laboratory experiment tracking system — data model"
requires-python = ">=3.11"
dependencies = [
    "sqlmodel>=0.0.22",
    "sqlalchemy>=2.0.36",
    "psycopg[binary]>=3.2",
    "alembic>=1.14",
    "pydantic-settings>=2.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lab"]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "pytest-spec>=5",
    "ruff>=0.7",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--spec --cov=src/lab --cov-branch --cov-fail-under=100 --cov-report=term-missing"

[tool.coverage.run]
branch = true
source = ["src/lab"]

[tool.coverage.report]
show_missing = true
skip_covered = false
fail_under = 100
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 5: Create the `lab` package**

```bash
mkdir -p src/lab tests
touch src/lab/__init__.py tests/__init__.py
```

- [ ] **Step 6: Write the canary test at `tests/test_canary.py`**

```python
def test_lab_package_imports():
    import lab

    assert lab is not None
```

- [ ] **Step 7: Write `.env.example`**

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/lab
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/lab_test
```

- [ ] **Step 8: Write the minimal `Makefile`**

```makefile
.DEFAULT_GOAL := help

.PHONY: help setup test

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install Python deps via uv; copy .env.example to .env if missing
	uv sync
	@test -f .env || cp .env.example .env

test: ## Run pytest with 100% branch coverage enforced
	uv run pytest
```

- [ ] **Step 9: Install deps**

```bash
make setup
```

Expected: `uv sync` resolves and installs deps; `.env` is created from `.env.example`.

- [ ] **Step 10: Run tests, verify 100% coverage**

```bash
make test
```

Expected: `1 passed`. Coverage report: `TOTAL  0  0  0  0  100%` (zero statements in `src/lab/__init__.py`, so 100% by convention). No `--cov-fail-under` failure.

- [ ] **Step 11: Commit**

```bash
git add .gitignore .python-version pyproject.toml uv.lock src/ tests/ Makefile .env.example
git commit -m "chore: project skeleton with 100% branch coverage gate"
```

---

## Task 2: Docker Compose + DB Makefile targets

**Files:**
- Create: `docker-compose.yml`
- Modify: `Makefile`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: lab-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: lab
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 2: Extend the Makefile with up/down/db-shell/clean**

Append the following targets to `Makefile`:

```makefile
.PHONY: up down db-shell clean

up: ## Start Postgres (detached, waits for healthy)
	docker compose up -d --wait

down: ## Stop Postgres
	docker compose down

db-shell: ## Open psql against the lab database
	docker compose exec postgres psql -U postgres -d lab

clean: ## Stop and remove the Postgres volume (DESTRUCTIVE — asks first)
	@read -p "This will destroy the lab Postgres volume. Continue? [y/N] " ans && [ "$$ans" = "y" ] || exit 1
	docker compose down -v
```

- [ ] **Step 3: Verify the compose file parses**

```bash
docker compose config > /dev/null
```

Expected: exit code 0, no output to stderr.

- [ ] **Step 4: Bring up Postgres and verify healthy**

```bash
make up
docker compose ps
```

Expected: `lab-postgres` listed with status `healthy`.

- [ ] **Step 5: Smoke-test the DB connection**

```bash
docker compose exec -T postgres psql -U postgres -d lab -c "SELECT 1;"
```

Expected: `?column?\n----------\n        1\n(1 row)`.

- [ ] **Step 6: Re-run tests to confirm nothing broke**

```bash
make test
```

Expected: `1 passed`, coverage 100%.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml Makefile
git commit -m "feat: docker-compose postgres + make up/down/db-shell/clean"
```

---

## Task 3: Settings module (`src/lab/config.py`)

**Files:**
- Create: `src/lab/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests at `tests/test_config.py`**

```python
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
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'Settings' from 'lab.config'`.

- [ ] **Step 3: Write `src/lab/config.py`**

```python
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lab"
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/lab_test"

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 6 passed, coverage 100%.

If coverage < 100%, the missing-lines report will show which branch in `config.py` is uncovered. Both branches of `normalize_database_url` (`startswith` true / false) are covered by tests 4 and 5.

- [ ] **Step 6: Commit**

```bash
git add src/lab/config.py tests/test_config.py
git commit -m "feat: pydantic-settings config with psycopg URL normalization"
```

---

## Task 4: DB engine (`src/lab/db.py`)

**Files:**
- Create: `src/lab/db.py`
- Create: `tests/test_db.py`

**Setup:** Postgres must be running. `make up` if not.

- [ ] **Step 1: Ensure the `lab` database is reachable**

```bash
docker compose exec -T postgres psql -U postgres -d lab -c "SELECT 1;"
```

Expected: returns `1`.

- [ ] **Step 2: Write the failing tests at `tests/test_db.py`**

```python
from sqlalchemy import text

from lab.config import settings
from lab.db import engine


def test_engine_url_matches_settings():
    assert str(engine.url) == settings.DATABASE_URL


def test_engine_can_connect_and_query():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()

    assert result == 1
```

- [ ] **Step 3: Run, expect failure**

```bash
uv run pytest tests/test_db.py -v
```

Expected: `ImportError: cannot import name 'engine' from 'lab.db'`.

- [ ] **Step 4: Write `src/lab/db.py`**

```python
from sqlalchemy import create_engine

from lab.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)
```

- [ ] **Step 5: Run, expect pass**

```bash
uv run pytest tests/test_db.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 8 passed, coverage 100%.

- [ ] **Step 7: Commit**

```bash
git add src/lab/db.py tests/test_db.py
git commit -m "feat: SQLAlchemy sync engine bound to settings.DATABASE_URL"
```

---

## Task 5: Models package stub (`src/lab/models/`)

**Files:**
- Create: `src/lab/models/__init__.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test at `tests/test_models.py`**

```python
def test_models_module_exposes_sqlmodel_metadata():
    from lab.models import SQLModel

    assert SQLModel.metadata is not None
    # No aggregates yet — sorted_tables is empty until the schema design lands.
    assert list(SQLModel.metadata.sorted_tables) == []
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'lab.models'`.

- [ ] **Step 3: Create the models package**

```bash
mkdir -p src/lab/models
```

Write `src/lab/models/__init__.py`:

```python
"""Aggregate root re-exports.

This module is the single import point for `SQLModel.metadata` discovery,
used by Alembic's `env.py`. As aggregates land, import them here so their
table metadata is registered before autogenerate runs.
"""

from sqlmodel import SQLModel

__all__ = ["SQLModel"]
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 9 passed, coverage 100%.

- [ ] **Step 6: Commit**

```bash
git add src/lab/models/ tests/test_models.py
git commit -m "feat: models package stub with SQLModel re-export"
```

---

## Task 6: Alembic wiring

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/.gitkeep`
- Create: `tests/test_alembic.py`
- Modify: `Makefile` (add `migrate`, `migration`, `migrate-down`, `migrate-test`)

**Setup:** Postgres running, `lab` database exists, `lab_test` does not yet.

- [ ] **Step 1: Create the `lab_test` database** (one-time, idempotent)

```bash
docker compose exec -T postgres psql -U postgres -d postgres -c "CREATE DATABASE lab_test;" || true
```

Expected: success, or `ERROR: database "lab_test" already exists` (which `|| true` swallows).

- [ ] **Step 2: Write `alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create the alembic directory layout**

```bash
mkdir -p alembic/versions
touch alembic/versions/.gitkeep
```

- [ ] **Step 4: Write `alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from lab.config import settings
from lab.models import SQLModel  # noqa: F401 — populates SQLModel.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():  # pragma: no cover — alembic-only execution path
    run_migrations_offline()
else:  # pragma: no cover — alembic-only execution path
    run_migrations_online()
```

> **Why the `pragma: no cover` on the bottom branch:** `alembic/env.py` is excluded from `--cov` via the `source = ["src/lab"]` config; the pragmas are belt-and-suspenders so a reader doesn't wonder. The exclusion is also called out in the spec.

- [ ] **Step 5: Write `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Add Makefile targets**

Append to `Makefile`:

```makefile
.PHONY: migrate migration migrate-down migrate-test

migrate: ## Apply pending migrations to the lab database
	uv run alembic upgrade head

migration: ## Generate a new migration revision; usage: make migration m="describe change"
	@test -n "$(m)" || (echo "Usage: make migration m=\"description\""; exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrate-down: ## Downgrade N revisions; usage: make migrate-down N=1
	@test -n "$(N)" || (echo "Usage: make migrate-down N=1"; exit 1)
	uv run alembic downgrade -$(N)

migrate-test: ## Apply migrations to the lab_test database (used by pytest setup)
	@docker compose exec -T postgres psql -U postgres -d postgres -c "CREATE DATABASE lab_test;" 2>/dev/null || true
	DATABASE_URL="$$TEST_DATABASE_URL" uv run alembic upgrade head
```

- [ ] **Step 7: Verify `alembic upgrade head` runs against the empty schema**

```bash
make migrate
```

Expected: alembic creates the `alembic_version` table, exits 0. No revisions to apply (versions/ is empty).

- [ ] **Step 8: Verify the same against `lab_test`**

```bash
make migrate-test
```

Expected: same as above, but against `lab_test`.

- [ ] **Step 9: Write integration test at `tests/test_alembic.py`**

```python
from sqlalchemy import inspect

from lab.db import engine


def test_alembic_version_table_exists_after_migrate():
    """`make migrate` (run before pytest) must create alembic_version."""
    inspector = inspect(engine)

    assert "alembic_version" in inspector.get_table_names()
```

- [ ] **Step 10: Run, expect pass**

```bash
uv run pytest tests/test_alembic.py -v
```

Expected: 1 passed.

- [ ] **Step 11: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 10 passed, coverage 100%.

- [ ] **Step 12: Commit**

```bash
git add alembic.ini alembic/ tests/test_alembic.py Makefile
git commit -m "feat: alembic wiring with autogenerate against lab.models metadata"
```

---

## Task 7: Pytest conftest with transactional session fixture

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_conftest.py`
- Modify: `Makefile` — make `test` depend on `migrate-test` so the suite is self-sufficient

**Setup:** Postgres running. The `migrate-test` dependency on `test` (added in Step 1 below) ensures `alembic_version` exists in `lab_test` before pytest runs.

- [ ] **Step 1: Make `test` depend on `migrate-test` in the Makefile**

Edit the `test` target in `Makefile` so it reads:

```makefile
test: migrate-test ## Run pytest with 100% branch coverage enforced
	uv run pytest
```

Sanity-check:

```bash
make test
```

Expected: `migrate-test` runs first (creates/upgrades `lab_test`), then pytest runs the existing suite (10 passed at this point, coverage 100%).

- [ ] **Step 2: Write `tests/conftest.py`**

```python
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine, event
from sqlmodel import Session

from lab.config import settings


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    engine = create_engine(settings.TEST_DATABASE_URL, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(test_engine: Engine) -> Iterator[Session]:
    """Per-test session with SAVEPOINT-based rollback isolation.

    Each test runs inside an outer transaction. A SAVEPOINT is opened so
    that `session.commit()` inside the test commits the savepoint (not
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
```

- [ ] **Step 3: Write fixture tests at `tests/test_conftest.py`**

```python
from sqlalchemy import text
from sqlmodel import Session


def test_db_fixture_yields_open_session(db: Session):
    assert db.is_active

    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_db_fixture_allows_inner_commit_within_savepoint(db: Session):
    """An inner commit should not raise; the savepoint restarts under the hood."""
    db.execute(text("CREATE TEMP TABLE _marker (x INT) ON COMMIT DROP"))
    db.execute(text("INSERT INTO _marker VALUES (1)"))
    db.commit()  # commits the SAVEPOINT; outer transaction still open

    # The temp table is dropped by ON COMMIT DROP at savepoint release;
    # this assertion proves the inner commit cycle actually ran.
    tables = db.execute(
        text("SELECT count(*) FROM information_schema.tables WHERE table_name = '_marker'")
    ).scalar()
    assert tables == 0


def test_db_fixture_rolls_back_test_isolation_first(db: Session):
    """Part 1 of an isolation pair: insert a marker into a real table."""
    db.execute(text("INSERT INTO alembic_version (version_num) VALUES ('isolation_marker')"))
    db.commit()

    count = db.execute(
        text("SELECT count(*) FROM alembic_version WHERE version_num = 'isolation_marker'")
    ).scalar()
    assert count == 1


def test_db_fixture_rolls_back_test_isolation_second(db: Session):
    """Part 2: previous test's marker must not be visible — proof of rollback."""
    count = db.execute(
        text("SELECT count(*) FROM alembic_version WHERE version_num = 'isolation_marker'")
    ).scalar()
    assert count == 0
```

- [ ] **Step 4: Run conftest tests, expect pass**

```bash
uv run pytest tests/test_conftest.py -v
```

Expected: 4 passed. (Pytest preserves file order; isolation tests rely on `first` running before `second` — they live in the same file so this holds.)

- [ ] **Step 5: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 14 passed, coverage 100%.

If branch coverage on the `_restart_savepoint` listener reports a miss, check that at least one of the conftest tests triggered the `transaction.nested` branch — `test_db_fixture_allows_inner_commit_within_savepoint` is the one that does so.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_conftest.py Makefile
git commit -m "test: conftest with SAVEPOINT-isolated per-test session fixture"
```

---

## Task 8: Seed stub (`src/lab/seed.py`)

**Files:**
- Create: `src/lab/seed.py`
- Create: `tests/test_seed.py`

- [ ] **Step 1: Write the failing test at `tests/test_seed.py`**

```python
from sqlmodel import Session

from lab.seed import seed


def test_seed_runs_against_a_session_without_error(db: Session):
    seed(db)
    # No assertions on data — the schema design will add real seed scenarios.
    # Just proves the entry point is callable.
    assert db.is_active
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/test_seed.py -v
```

Expected: `ModuleNotFoundError: No module named 'lab.seed'`.

- [ ] **Step 3: Write `src/lab/seed.py`**

```python
"""Seed entry point.

Currently a no-op stub. Real seed scenarios land with the schema design;
see docs/superpowers/specs/2026-05-12-core-infra-design.md for the four
spec-required scenarios that will be exercised here.
"""

from sqlmodel import Session

from lab.db import engine


def seed(session: Session) -> None:
    """Apply seed data to the given session. No-op until schema lands."""
    return


if __name__ == "__main__":  # pragma: no cover
    with Session(engine) as session:
        seed(session)
        session.commit()
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/test_seed.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Verify full-suite coverage still 100%**

```bash
make test
```

Expected: 15 passed, coverage 100%.

- [ ] **Step 6: Commit**

```bash
git add src/lab/seed.py tests/test_seed.py
git commit -m "feat: seed entry point stub (no-op until schema lands)"
```

---

## Task 9: Round out the Makefile

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Append remaining targets**

Append to `Makefile`:

```makefile
.PHONY: seed start test-one coverage lint format

seed: ## Apply seed data to the lab database
	uv run python -m lab.seed

start: ## One-command bootstrap: up + migrate + seed
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed

test-one: ## Run a single test path; usage: make test-one T=tests/test_foo.py::test_bar
	@test -n "$(T)" || (echo "Usage: make test-one T=tests/path::test_name"; exit 1)
	uv run pytest $(T) -v

coverage: ## Run pytest and open the HTML coverage report
	uv run pytest --cov-report=html
	@command -v open >/dev/null 2>&1 && open htmlcov/index.html || echo "Open htmlcov/index.html manually"

lint: ## Lint with ruff
	uv run ruff check .

format: ## Format with ruff
	uv run ruff format .
```

- [ ] **Step 2: Verify `make help` lists every documented target**

```bash
make help
```

Expected output includes: `help`, `setup`, `test`, `up`, `down`, `db-shell`, `clean`, `migrate`, `migration`, `migrate-down`, `migrate-test`, `seed`, `start`, `test-one`, `coverage`, `lint`, `format`.

- [ ] **Step 3: Verify `make start` end-to-end works**

```bash
make down
make start
```

Expected: postgres comes up healthy, `alembic upgrade head` runs (creates `alembic_version`), `seed` runs as a no-op.

- [ ] **Step 4: Verify `make lint` and `make format` pass**

```bash
make lint
make format
```

Expected: no diagnostics; format is a no-op (already formatted).

- [ ] **Step 5: Verify `make coverage` produces HTML**

```bash
make coverage
ls htmlcov/index.html
```

Expected: `htmlcov/index.html` exists. (`open` may not run on non-Darwin / non-GUI; tolerated.)

- [ ] **Step 6: Re-run the suite**

```bash
make test
```

Expected: 15 passed, coverage 100%.

- [ ] **Step 7: Commit**

```bash
git add Makefile
git commit -m "feat: round out makefile with seed/start/coverage/lint/format/test-one"
```

---

## Task 10: README + future-enhancements doc

**Files:**
- Create: `README.md`
- Create: `docs/future-enhancements.md`

> **Note:** The README's "tradeoffs," "assumptions," and "open questions" sections are *infra-scoped only* at this point. The schema follow-up will expand them with the real data-model decisions.

- [ ] **Step 1: Write `docs/future-enhancements.md`**

```markdown
# Future Enhancements

Items deliberately not built into the core infra. Captured here so they
don't bloat the take-home or get forgotten.

## Enhancement A — FastAPI surface

**Why later:** The spec asks for a data model, not an API. Models exist in
`src/lab/models/`; SQLModel doubles as Pydantic response schemas, so this
add is roughly an hour.

**Sketch:**
- `src/lab/api/` package with one router per aggregate
- Each handler: `with Session(engine) as s: return s.exec(select(...)).all()`
- Add `api` service to `docker-compose.yml`; `make api` runs uvicorn
- Free Swagger UI at `/docs`

## Enhancement B — Async SQLAlchemy

**Why later:** No concurrent consumer needs it. Async is ceremony without
benefit at this scale.

**Sketch:** swap `create_engine` → `create_async_engine`, sessions to
`AsyncSession`. Touches `db.py` and `conftest.py`. ~30 min.

## Enhancement C — Robot Framework acceptance tests

**Why later:** Depends on Enhancement A (no API surface to exercise yet).

**Sketch:** `acceptance/*.robot` suites using `robotframework-requests`.
Lives outside compose; reviewers run `uv run robot acceptance/`.

## Enhancement D — Possible follow-ups post-exercise

Things worth building in a real system, captured to keep them out of the
take-home:

- **Audit trail for measurements** — labs care who recorded what and when;
  immutable `measurement_events` feeding a materialized view
- **Soft delete** for projects and experiments — research orgs don't
  actually discard data
- **Attachments object store** — labs produce images, gels, chromatograms
- **Authn/authz enforcement** — roles already in schema; no enforcement layer
- **Full-text search** — Postgres FTS first; Elasticsearch only if it earns it
- **Sample lineage** — derived/subdivided samples not captured by current
  experiment-sample join
- **Time-series partitioning for numeric measurements** — partitioned tables
  or TimescaleDB if volume grows
- **REST vs GraphQL** — decide when client read patterns vary
- **Mutation testing** — `mutmut` or `cosmic-ray` to verify tests kill
  mutants, not just touch lines (complement to the 100% coverage gate)
- **Down-migration tooling beyond Alembic's built-in** — currently no CI
  gate on rollback safety
```

- [ ] **Step 2: Write `README.md`**

```markdown
# Lab Experiment Tracking — Data Model

Take-home exercise. Designs the Postgres data model that will sit under a
laboratory experiment tracking system. The deliverable is the schema +
seed data + this README; see [`lab-experiment-tracking-system.md`](./lab-experiment-tracking-system.md)
for the full brief.

> **Status:** Core infra only. The schema design lands in a follow-up.

## Quick start

```bash
make start
```

That's it. The command brings up Postgres, applies migrations, and runs
seed. Confirm with:

```bash
make db-shell
\dt
```

## Prerequisites

- Docker + Docker Compose
- [`uv`](https://docs.astral.sh/uv/) (Python package manager)

## What's here

```
.
├── docker-compose.yml         # postgres:16-alpine, one service
├── Makefile                   # `make help` lists everything
├── alembic/                   # migrations (Alembic, autogenerated from models)
├── src/lab/
│   ├── config.py              # pydantic-settings (DATABASE_URL et al.)
│   ├── db.py                  # SQLAlchemy 2.x sync engine
│   ├── models/                # SQLModel classes — schema source of truth
│   └── seed.py                # seed entry point
├── tests/                     # pytest, 100% branch coverage enforced
└── docs/
    ├── superpowers/specs/     # design docs
    ├── superpowers/plans/     # implementation plans
    └── future-enhancements.md # things deliberately not built
```

## Tests

```bash
make test           # 100% branch coverage enforced; fails otherwise
make coverage       # opens htmlcov/index.html
```

The coverage gate is enforced commit-by-commit via `pyproject.toml`
addopts (`--cov-branch --cov-fail-under=100`). A change that drops
coverage cannot land.

## Assumptions (infra-level)

- Python 3.11+ is acceptable (CI/host).
- Reviewers run `make start` once and don't need the test database
  pre-created — `make migrate-test` handles it lazily.
- Postgres 16 specifically. No effort spent on cross-version compatibility.

> Schema-level assumptions (researcher roles, measurement polymorphism,
> cascade behavior, etc.) land with the schema follow-up.

## Tradeoffs (infra-level)

- **Two schema representations.** Models in `src/lab/models/` are
  source-of-truth for *changes*; generated Alembic migrations are
  source-of-truth for *what's deployed*. Reviewers should read the
  migrations as the deliverable; the models are the authoring tool.
- **Sync, not async.** No HTTP layer to demand async. Captured as
  Enhancement B if it ever becomes necessary.
- **100% branch coverage as a build gate.** The cost is that every
  conditional in `db.py`/`config.py`/`seed.py` must be covered. The
  benefit is design pressure — untested branches become a design
  problem to solve, not a TODO to defer.
- **No FastAPI / HTTP surface.** Considered and explicitly chose not to.
  The spec asks for a data model; adding an API would be vanity work.
  Roughly an hour to add if needed — see Enhancement A.

## Open questions (infra-level)

- Should CI gate down-migrations too, or accept "rollback is a runbook
  step" as the SLA?
- Should reviewers see a more elaborate `make start` (e.g., one that
  rebuilds from clean) or is current behavior good enough?

> Schema-level open questions land with the schema follow-up.

## Future enhancements

See [`docs/future-enhancements.md`](./docs/future-enhancements.md).
```

- [ ] **Step 3: Verify the README renders cleanly**

```bash
# Just visually check
less README.md
```

Expected: code fences close, links resolve, no obvious typos.

- [ ] **Step 4: Final full-suite run**

```bash
make test
```

Expected: 15 passed, coverage 100%.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/future-enhancements.md
git commit -m "docs: README + future-enhancements notes (infra scope)"
```

---

## Final verification

- [ ] **Step 1: Clean-room bootstrap proves the one-command works**

```bash
make down
make clean        # destroys volume (answer 'y')
make setup
make start
make test
```

Expected: every command exits 0. `make test` reports 15 passed, coverage 100%.

- [ ] **Step 2: Confirm git state is clean**

```bash
git status
```

Expected: `nothing to commit, working tree clean`.

---

## Coverage of the spec

| Spec requirement | Task(s) |
|---|---|
| Postgres 16 in docker-compose with healthcheck | Task 2 |
| `make start` one-command bootstrap | Task 9 |
| SQLModel + SQLAlchemy 2.x sync + psycopg | Tasks 1, 4 |
| Alembic with autogenerate from `lab.models` | Task 6 |
| `pydantic-settings` for config | Task 3 |
| Two databases (`lab`, `lab_test`) on one container | Tasks 2, 6 |
| Sync conftest with SAVEPOINT-isolated per-test session | Task 7 |
| 100% branch coverage gate from commit #1 | Tasks 1 (config), all tasks (enforced) |
| Excluded: `alembic/versions/**`, `alembic/env.py`, `__main__` shims | Task 1 (config), Task 6 (env.py pragmas), Task 8 (seed `__main__`) |
| Self-documenting Makefile via `## comments` | Tasks 1, 2, 6, 9 |
| Tradeoffs / assumptions / open questions in README | Task 10 |
| Future enhancements captured | Task 10 |
| Seed entry point (no-op stub until schema lands) | Task 8 |
| `ruff` lint + format | Tasks 1, 9 |

Schema design (researcher/project/experiment/sample/measurement modeling,
polymorphic measurement strategy, status enums, ID strategy, cascade
behavior) is deliberately deferred to the follow-up plan — that's the
*next* spec + plan cycle, not part of this one.
