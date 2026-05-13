"""Load test for schema validation under volume.

See docs/superpowers/specs/2026-05-13-load-test-design.md for the design.

Runs against a separate ``lab_load`` Postgres database; idempotent (each
invocation truncates and reloads). Outputs a per-query report to stdout.

Usage:
    uv run python -m scripts.load_test --rows 100000
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

import psycopg

from lab.config import get_settings


@dataclass(frozen=True)
class Plan:
    """Row counts for each entity at a given measurement-row target.

    Proportions chosen to keep FK distribution realistic — enough cardinality
    per parent that the planner sees meaningful index selectivity. Floors keep
    the dataset usable at very small N (e.g., N=1000 still produces ≥4 researchers).
    """

    rows: int
    researchers: int
    projects: int
    memberships: int
    samples: int
    experiments: int
    experiment_samples: int
    measurements: int


def plan_for(rows: int) -> Plan:
    """Compute proportional row counts from the target measurement count."""
    researchers = max(rows // 50_000, 4)
    projects = max(rows // 20_000, 5)
    samples = max(rows // 5_000, 20)
    experiments = max(rows // 10_000, 10)
    return Plan(
        rows=rows,
        researchers=researchers,
        projects=projects,
        memberships=min(researchers * projects, max(rows // 5_000, 20)),
        samples=samples,
        experiments=experiments,
        experiment_samples=max(rows // 2_500, 40),
        measurements=rows,
    )


def load_database_url() -> str:
    """Derive the lab_load DB URL from the dev DATABASE_URL by swapping the db name."""
    dev_url = get_settings().DATABASE_URL
    base, _ = dev_url.rsplit("/", 1)
    return f"{base}/lab_load"


def _admin_url() -> str:
    """URL pointing at the system 'postgres' database for CREATE DATABASE.

    Strips the SQLAlchemy ``+psycopg`` dialect marker — psycopg's libpq
    parser only understands plain ``postgresql://`` URIs.
    """
    dev_url = get_settings().DATABASE_URL
    base, _ = dev_url.rsplit("/", 1)
    base = base.replace("postgresql+psycopg://", "postgresql://", 1)
    return f"{base}/postgres"


def ensure_lab_load_database() -> None:
    """``CREATE DATABASE lab_load`` if it doesn't exist. Idempotent."""
    with psycopg.connect(_admin_url(), autocommit=True) as conn:
        try:
            conn.execute("CREATE DATABASE lab_load")
        except psycopg.errors.DuplicateDatabase:
            pass


def migrate(load_url: str) -> None:
    """Run alembic migrations against the load DB via subprocess.

    Subprocess reuses the existing alembic infrastructure (the Makefile's
    ``migrate-test`` target does the same dance). Avoids embedding alembic's
    Python API in the script.
    """
    env = {**os.environ, "DATABASE_URL": load_url}
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="load_test",
        description="Load the schema with N measurements and validate index usage.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=100_000,
        help="Number of measurements to load (default: 100,000).",
    )
    args = parser.parse_args(argv)

    plan = plan_for(args.rows)
    print(f"load_test: target N={plan.rows:,} measurements")

    print("load_test: ensuring lab_load database exists...")
    ensure_lab_load_database()

    load_url = load_database_url()
    print(f"load_test: applying migrations to {load_url}...")
    migrate(load_url)

    print("load_test: ready (no rows loaded yet — that lands in Task 5)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
