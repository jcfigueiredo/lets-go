# Core Infrastructure Design — Lab Experiment Tracking

**Status:** Approved (pending sign-off on this written form)
**Date:** 2026-05-12
**Author:** Claudio + Claude
**Scope:** Core infra only — the data model and seed data are out of scope for this document and land in a follow-up.

## Context

This repo is the take-home for a "Laboratory Experiment Tracking System" interview. The full brief is in [`lab-experiment-tracking-system.txt`](../../../lab-experiment-tracking-system.txt). The deliverable per the spec is:

1. Data model implemented as Postgres migrations
2. Single-command Docker bootstrap producing a running Postgres with schema + seed data
3. README covering bootstrap, assumptions, tradeoffs (including ≥1 thing deliberately not done), open questions

This document defines the infrastructure that will host (1) and (2). The schema itself is deferred to a follow-up design.

## Scope

### In

- Postgres 16 in `docker-compose.yml`
- Alembic migrations generated from SQLModel classes
- SQLAlchemy 2.x (sync) over `psycopg[binary]`
- Python package `src/lab/` housing config, db wiring, models, seed
- `pytest` + `pytest-cov` for tests with **100% branch coverage enforced**
- `Makefile` as the single user-facing surface
- `uv` for Python deps, `ruff` for lint + format

### Deliberately out (YAGNI — see Tradeoffs)

- FastAPI / any HTTP API surface
- Robot Framework / any HTTP test framework
- Async (no consumer needs it)
- Auth, sessions, CSRF, CORS, telemetry, Redis, background tasks
- Frontend
- Service layer / UnitOfWork / DI framework
- Down-migration tooling beyond what Alembic gives for free

## Stack

| Concern | Choice | Note |
|---|---|---|
| DB | Postgres 16 (alpine) | docker-compose; healthcheck on `pg_isready` |
| Schema authoring | SQLModel classes in `src/lab/models/` | source of truth for *changes* |
| Migrations | Alembic with autogenerate | source of truth for *what's deployed* |
| Driver | `psycopg[binary]>=3.2` | sync |
| ORM | SQLAlchemy 2.x via SQLModel | |
| Config | `pydantic-settings` | `DATABASE_URL` + `TEST_DATABASE_URL` only |
| Tests | `pytest` + `pytest-cov` + `pytest-spec` | sync; transactional rollback per test |
| Lint/format | `ruff` | line-length 100; `select = ["E", "F", "I", "B", "UP"]` |
| Dep mgmt | `uv` | dev-only — runtime lives in the container |
| Entry point | `Makefile` | self-documenting via `## comments` |

## Repo layout

```
lets-go/
├── Makefile
├── docker-compose.yml
├── README.md
├── .env.example
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                   # the deliverable per spec
├── src/lab/
│   ├── __init__.py
│   ├── config.py                   # pydantic-settings
│   ├── db.py                       # sync engine + sessionmaker
│   ├── models/                     # SQLModel classes
│   │   ├── __init__.py             # re-exports; populates SQLModel.metadata
│   │   ├── researcher.py
│   │   ├── project.py
│   │   ├── experiment.py
│   │   ├── sample.py
│   │   └── measurement.py
│   └── seed.py                     # `python -m lab.seed`
├── tests/
│   ├── conftest.py                 # engine + transactional session fixtures
│   ├── test_schema.py              # constraints, FKs, enums, polymorphism
│   ├── test_seed.py                # asserts the four spec-required scenarios
│   └── test_queries.py             # representative reads
└── docs/
    ├── superpowers/specs/2026-05-12-core-infra-design.md   # this file
    └── future-enhancements.md
```

## docker-compose.yml

One service:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: lab-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: lab
    ports: ["5432:5432"]
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

`lab_test` is created on demand by the Makefile target `migrate-test`, which runs `docker compose exec -T postgres createdb -U postgres --if-exists=skip lab_test` (or equivalent idempotent CREATE DATABASE) before applying migrations against it.

## Migrations strategy

Schema is authored in `src/lab/models/`; Alembic generates migration files in `alembic/versions/`. Workflow:

```
make migration m="initial schema"   # alembic revision --autogenerate -m "..."
$EDITOR alembic/versions/<hash>_initial_schema.py   # review, tidy, add what autogen misses
make migrate                                        # alembic upgrade head
```

Autogenerate is treated as a draft, not a deliverable. CHECK constraints, partial indexes, and any non-trivial DDL get hand-edited into the generated revision.

**`alembic/env.py` deviations from default:**
- Reads `DATABASE_URL` from `lab.config.settings`
- Imports `lab.models` so `SQLModel.metadata` is populated before `target_metadata = SQLModel.metadata`
- `compare_type=True` in `context.configure(...)` — autogenerate notices column-type changes

**Open call (resolved):** No async branch in `env.py`. Re-add if/when async lands.

## Test architecture

Sync. One Postgres container, two databases: `lab` (dev/seed) and `lab_test` (tests).

**Fixture pattern** in `tests/conftest.py`:

- Session-scoped engine pointing at `TEST_DATABASE_URL`
- Per-test `db` fixture opens a connection, begins an outer transaction, opens a SAVEPOINT, yields a `Session`, then rolls everything back

This means tests can `commit()` (e.g., to test constraint behavior at commit-time) without leaking state across tests.

**Test files:**
- `test_schema.py` — constraints, FK behavior, enum values, polymorphic-measurement CHECK constraints
- `test_seed.py` — asserts seed satisfies the four spec scenarios: ≥1 project with ≥2 researchers, ≥1 experiment with a follow-up reference, ≥1 sample used by ≥2 experiments, measurements covering ≥2 kinds
- `test_queries.py` — representative reads (e.g., "all measurements for project X by experiment", "samples used across the most experiments") — doubles as interview-extension ammo

**Workflow:** `make up && make migrate-test && make test`.

## Coverage policy (commit-by-commit, 100%, branch)

**Enforcement** — in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
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
```

Plain `pytest` (and therefore `make test`) fails if branch coverage on `src/lab` drops below 100%. CI is just `make test`.

**Excluded by design:**

| Path / pattern | Reason |
|---|---|
| `alembic/versions/**` | Generated code; behavior tested via `test_schema.py` post-migrate |
| `alembic/env.py` | Runs only in Alembic's process, not pytest's |
| `# pragma: no cover` blocks | Only with an inline comment justifying *why* (e.g., unreachable per upstream invariant) |
| `if __name__ == "__main__":` | Entry-point shim; the called function itself is covered |

**What the gate prevents:**
- ❌ Coverage theater — import-only tests are insufficient under branch coverage
- ❌ Land-now-test-later steps — every implementation step must include its tests
- ❌ Deferring tests for "obvious" model declarations — declarations don't trip branch coverage; the *logic* in `db.py`/`seed.py`/`config.py` does

**What the gate doesn't replace:**
- Tests that assert *behavior*, not just execution. Coverage = 100% with `assert True` is still passing — test *design* matters more than the gate.
- Mutation testing. Captured in future enhancements as a possible follow-up.

## Makefile surface

Self-documenting via `## comments` parsed into `make help`.

```
make help                # default; lists documented targets
make setup               # uv sync; cp .env.example .env if missing
make up                  # docker compose up -d
make down                # docker compose down
make start               # docker compose up -d --wait, then migrate + seed  ← the README's one command
make migrate             # alembic upgrade head against lab
make migration m="..."   # alembic revision --autogenerate -m "..."
make migrate-down N=1    # alembic downgrade -N
make migrate-test        # alembic upgrade head against lab_test (used before make test)
make seed                # python -m lab.seed
make test                # pytest (100% branch coverage enforced)
make test-one T=path     # pytest <path>
make coverage            # pytest + open htmlcov/index.html
make lint                # ruff check
make format              # ruff format
make db-shell            # psql into lab
make clean               # down -v (asks before destroying volume)
```

## pyproject.toml shape

```toml
[project]
name = "lab"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "sqlmodel>=0.0.22",
  "sqlalchemy>=2.0.36",
  "psycopg[binary]>=3.2",
  "alembic>=1.14",
  "pydantic-settings>=2.6",
]

[dependency-groups]
dev = [
  "pytest>=8",
  "pytest-cov>=5",
  "pytest-spec>=5",
  "ruff>=0.7",
]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

## Open design calls (resolved here)

1. **Container-everything for the bootstrap, host-side for the test runner.** Postgres runs in compose; `pytest` runs on the host against the exposed port. Adding a test container just to run pytest against another container is over-engineered.
2. **Single Postgres container, two databases.** `lab` and `lab_test` share the container; `Makefile` creates `lab_test` on demand.
3. **No down-migration tooling beyond Alembic's built-in.** `make migrate-down N=1` exists but isn't exercised in tests or CI.
4. **`uv` over pip-tools/poetry.** Matches user's other Python projects.
5. **No mypy.** `ruff` + SQLModel typing pressure is enough at this scale; mypy lands in future enhancements only if generic types start surprising us.
6. **Package name `lab`.** Short, matches the domain, no collision.

## Tradeoffs (for the README's "tradeoffs" section)

Surfacing these now so they don't get reconstructed later:

1. **Two schema representations** (Python models + generated SQL migrations). Authoring lives in models; deployment runs the migrations. Reviewers should read the migrations as the deliverable; models are the authoring tool. We accept the duplication for the autogenerate ergonomics.
2. **No FastAPI / API surface.** Deliberately chose not to build an HTTP layer — the spec asks for a data model, not an API. Adding one is captured as Enhancement A.
3. **Sync, not async.** Without a concurrent consumer, async is ceremony without benefit. Captured as Enhancement B.
4. **No down-migrations in CI.** Alembic gives us the command; we don't gate on it. Real production systems would; a take-home doesn't need to.
5. **100% branch coverage as a gate.** The cost is that every conditional in `db.py`/`seed.py`/`config.py` must have a test. The benefit is the design pressure: untested branches become a design problem to solve, not a TODO to defer.

## Future enhancements (separate file)

Full notes in [`docs/future-enhancements.md`](../../future-enhancements.md) — created during implementation. Headlines:

- **A — FastAPI surface** (~1h with models in place; SQLModel doubles as Pydantic schemas)
- **B — Async SQLAlchemy** (~30min once a concurrent consumer exists)
- **C — Robot Framework acceptance** (depends on A)
- **D — Possible follow-ups post-exercise:** audit trail for measurements, soft delete, attachments object store, authz enforcement, full-text search, sample lineage, time-series partitioning (TimescaleDB?), API surface choice (REST vs GraphQL), mutation testing (`mutmut`/`cosmic-ray`)

## What this design does NOT decide

These are deliberately deferred to the schema design (separate document):

- The polymorphic measurement strategy (single-table with nullable columns vs. JSONB vs. joined inheritance)
- Whether researcher role is global or per-project
- Cascade behavior (delete project → experiments? hard delete or soft?)
- Sample-storage and sample-collection-context modeling
- Whether to share the `status` enum between Project and Experiment
- ID strategy (sequential bigint vs. UUID v7)

All of the above land in the schema design follow-up, *not* here.
