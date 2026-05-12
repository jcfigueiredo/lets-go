# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This is a **take-home interview exercise** for a "laboratory experiment tracking system." Spec at `lab-experiment-tracking-system.txt`. Design at `docs/superpowers/specs/2026-05-12-core-infra-design.md`. Implementation plan at `docs/superpowers/plans/2026-05-12-core-infra.md`.

**Current state:** Core infra landed. Schema design (Researcher/Project/Experiment/Sample/Measurement) is **deferred** to a follow-up spec + plan cycle.

## What this project is

A data model for a **laboratory experiment tracking system**, delivered as Postgres migrations + Docker + seed data. The full brief is in `lab-experiment-tracking-system.txt`; read it before designing anything. Key entities and the relationships that drive the schema:

- **Researchers** ↔ **Projects**: many-to-many (researchers collaborate on multiple projects; projects have multiple researchers). Roles (PI, lab tech, grad student, …) are tracked per researcher — open question whether role is global or per-project.
- **Projects** → **Experiments**: one-to-many. Every experiment belongs to **exactly one** project.
- **Experiments** ↔ **Samples**: many-to-many (a sample can be used across experiments; an experiment uses multiple samples).
- **Experiments** → **Experiments**: self-reference for follow-ups (replication, iteration, refined hypothesis).
- **Measurements** → **Experiment** (required) + **Sample** (usually, not always). Measurements are **polymorphic**: numeric-with-unit, categorical, or free-text. "New kinds of measurements are added occasionally" — the schema must accommodate new measurement types without migrations to add columns per type. This is the single most interesting design decision in the model.
- Both Projects and Experiments have **lifecycle status** (planning/active/completed/cancelled for projects; experiments have their own status). Decide whether to share an enum or keep them separate.

## Required deliverables (from the spec)

1. **Single-command bootstrap**: `make start` → Postgres running with schema + seed data.
2. **Seed data that exercises the interesting parts** — at minimum: one project with multiple researchers, an experiment that references an earlier experiment, a sample used across multiple experiments, and measurements of more than one kind.
3. **README** covering: (a) the one-command bootstrap, (b) assumptions made about ambiguities, (c) tradeoffs including **at least one thing deliberately not done**, (d) open questions for the lab.

## Commands

The Makefile is the only user-facing surface. `make help` lists everything. Key targets:

- `make start` — one-command bootstrap (up + migrate + seed)
- `make up` / `make down` — start/stop Postgres
- `make migrate` — apply pending migrations
- `make migration m="…"` — autogenerate a new revision
- `make test` — pytest with 100% branch coverage enforced (depends on `migrate-test`)
- `make test-one T=path` — run a single test (no coverage gate)
- `make coverage` — pytest + open HTML report (depends on `migrate-test`)
- `make lint` / `make format` — ruff
- `make db-shell` — psql into lab
- `make clean` — destroy volume (prompts)

## Architecture

- Postgres 16 in `docker-compose.yml` on a **dynamically assigned host port**. `make up` writes the actual port into `.env`. Do not hard-code `localhost:5432`.
- `src/lab/`: `config.py` (pydantic-settings), `db.py` (sync engine), `models/` (SQLModel — schema source of truth, currently empty), `seed.py` (no-op stub).
- `alembic/`: env.py reads `get_settings().DATABASE_URL`; `make migrate-test` overrides to `TEST_DATABASE_URL` via shell.
- `tests/conftest.py`: autouse env-isolation fixture, session-scoped `test_engine` bound to `TEST_DATABASE_URL`, per-test `db` fixture using the canonical SQLAlchemy SAVEPOINT pattern.

## How to approach work here

The take-home spec explicitly says: *"We'd much rather see a decisive model built on explicit assumptions than a hesitant one that hedges against every possibility."* This shapes how to make decisions:

- **Decide and document, don't hedge.** When the spec is ambiguous, pick a defensible answer and write the assumption into the README.
- **The interview extends this live.** Choices will be defended and modified in a follow-up session. Favor designs that are easy to explain.
- **Measurement polymorphism is the load-bearing design call** for the schema follow-up.

## Coverage discipline

100% branch coverage is enforced from commit #1 via `addopts` in `pyproject.toml`. Every commit must pass `make test`. Excluded from coverage: `alembic/versions/**`, `alembic/env.py`, `__main__` shims, anything marked `# pragma: no cover` (with an inline comment justifying why).
