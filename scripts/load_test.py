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
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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


def _psycopg_url(url: str) -> str:
    """Strip the SQLAlchemy ``+psycopg`` dialect marker for libpq's URI parser.

    SQLAlchemy URLs (e.g. ``postgresql+psycopg://...``) carry a dialect marker
    that libpq doesn't recognize. ``psycopg.connect()`` parses URLs via libpq,
    so we strip the marker before handing the URL to psycopg directly.
    """
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _admin_url() -> str:
    """URL pointing at the system 'postgres' database for CREATE DATABASE.

    Strips the SQLAlchemy ``+psycopg`` dialect marker for libpq.
    """
    dev_url = get_settings().DATABASE_URL
    base, _ = dev_url.rsplit("/", 1)
    return _psycopg_url(f"{base}/postgres")


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


def truncate_all(conn: psycopg.Connection) -> None:
    """Empty every data table; reset id sequences.

    ``CASCADE`` handles the FK chain in one statement. ``RESTART IDENTITY``
    resets the bigserial sequences so loaded data starts at id=1.
    """
    conn.execute("""
        TRUNCATE measurements,
                 experiment_samples,
                 experiments,
                 samples,
                 project_researchers,
                 projects,
                 researchers
        RESTART IDENTITY CASCADE
    """)


_ROLES = (
    "principal_investigator",
    "lab_technician",
    "graduate_student",
    "postdoc",
    "undergraduate",
)
_PROJECT_STATUSES = ("planning", "active", "completed", "cancelled")
_EXPERIMENT_STATUSES = ("planned", "running", "completed", "cancelled")
_SPECIMEN_TYPES = ("blood", "tissue", "soil", "chemical_compound", "water")
_UNITS_NUMERIC = ("mg/dL", "ng/mL", "°C", "pH", "mmol/L")
_VALUES_CATEGORICAL = ("positive", "negative", "pass", "fail", "inconclusive")
_RNG = random.Random()  # module-level so each call deepens determinism across calls


def bulk_load(conn: psycopg.Connection, plan: Plan) -> None:
    """Bulk-insert N rows in dependency order via psycopg COPY.

    Captures IDs from each insert phase to feed FKs in subsequent phases.
    """
    cur = conn.cursor()

    # Phase 1: researchers (independent)
    with cur.copy("COPY researchers (name, email, role) FROM STDIN") as cp:
        for i in range(plan.researchers):
            cp.write_row((
                f"Researcher {i:05d}",
                f"researcher-{i:05d}@lab.example",
                _RNG.choice(_ROLES),
            ))
    researcher_ids = [row[0] for row in cur.execute(
        "SELECT id FROM researchers ORDER BY id"
    ).fetchall()]

    # Phase 2: projects (independent)
    with cur.copy("COPY projects (title, description, status) FROM STDIN") as cp:
        for i in range(plan.projects):
            cp.write_row((
                f"Project {i:05d}",
                f"Description for project {i:05d}.",
                _RNG.choice(_PROJECT_STATUSES),
            ))
    project_ids = [row[0] for row in cur.execute(
        "SELECT id FROM projects ORDER BY id"
    ).fetchall()]

    # Phase 3: project_researchers (m:n)
    # Pick `plan.memberships` distinct (project, researcher) pairs.
    pairs: set[tuple[int, int]] = set()
    while len(pairs) < plan.memberships:
        pairs.add((_RNG.choice(project_ids), _RNG.choice(researcher_ids)))
    with cur.copy("COPY project_researchers (project_id, researcher_id) FROM STDIN") as cp:
        for project_id, researcher_id in pairs:
            cp.write_row((project_id, researcher_id))

    # Phase 4: samples (independent)
    base_dt = datetime(2026, 1, 1, tzinfo=UTC)
    with cur.copy(
        "COPY samples (accession_code, specimen_type, collected_at, storage_location) FROM STDIN"
    ) as cp:
        for i in range(plan.samples):
            cp.write_row((
                f"LOAD-{i:08d}",
                _RNG.choice(_SPECIMEN_TYPES),
                base_dt + timedelta(days=i),
                f"Freezer {i % 10} / Shelf {i % 5} / Box {i % 20}",
            ))
    sample_ids = [row[0] for row in cur.execute(
        "SELECT id FROM samples ORDER BY id"
    ).fetchall()]

    # Phase 5: experiments (depend on projects; some reference earlier experiments)
    with cur.copy(
        "COPY experiments (project_id, title, hypothesis, start_date, end_date, status) FROM STDIN"
    ) as cp:
        for i in range(plan.experiments):
            start = (base_dt + timedelta(days=i * 7)).date()
            end = start + timedelta(days=14)
            cp.write_row((
                _RNG.choice(project_ids),
                f"Experiment {i:05d}",
                f"Hypothesis text for experiment {i:05d}.",
                start,
                end,
                _RNG.choice(_EXPERIMENT_STATUSES),
            ))
    experiment_ids = [row[0] for row in cur.execute(
        "SELECT id FROM experiments ORDER BY id"
    ).fetchall()]

    # Phase 5b: backfill follows_up_experiment_id on ~10% of experiments
    # (only ones whose id > the smallest id, so they reference an earlier one)
    follow_up_count = max(plan.experiments // 10, 1)
    candidates = experiment_ids[1:]  # exclude the first (no earlier experiment exists)
    if candidates:
        for child_id in _RNG.sample(candidates, k=min(follow_up_count, len(candidates))):
            parent_id = _RNG.choice([e for e in experiment_ids if e < child_id])
            cur.execute(
                "UPDATE experiments SET follows_up_experiment_id = %s WHERE id = %s",
                (parent_id, child_id),
            )

    # Phase 6: experiment_samples (m:n)
    es_pairs: set[tuple[int, int]] = set()
    while len(es_pairs) < plan.experiment_samples:
        es_pairs.add((_RNG.choice(experiment_ids), _RNG.choice(sample_ids)))
    with cur.copy("COPY experiment_samples (experiment_id, sample_id) FROM STDIN") as cp:
        for experiment_id, sample_id in es_pairs:
            cp.write_row((experiment_id, sample_id))

    # Phase 7: measurements (the headline volume)
    with cur.copy(
        """COPY measurements (
            experiment_id, sample_id, recorded_by, recorded_at,
            kind, numeric_value, unit, categorical_value, text_value, notes
        ) FROM STDIN"""
    ) as cp:
        for i in range(plan.measurements):
            kind = _RNG.choices(
                ("numeric", "categorical", "text"),
                weights=(60, 30, 10),
            )[0]
            experiment_id = _RNG.choice(experiment_ids)
            sample_id = _RNG.choice(sample_ids) if _RNG.random() > 0.05 else None
            recorded_by = _RNG.choice(researcher_ids)
            recorded_at = base_dt + timedelta(seconds=i * 30)

            if kind == "numeric":
                numeric_value = Decimal(str(round(_RNG.uniform(0, 300), 2)))
                unit = _RNG.choice(_UNITS_NUMERIC)
                categorical_value = None
                text_value = None
            elif kind == "categorical":
                numeric_value = None
                unit = None
                categorical_value = _RNG.choice(_VALUES_CATEGORICAL)
                text_value = None
            else:  # text
                numeric_value = None
                unit = None
                categorical_value = None
                text_value = f"Observation note {i:08d}."

            cp.write_row((
                experiment_id,
                sample_id,
                recorded_by,
                recorded_at,
                kind,
                numeric_value,
                unit,
                categorical_value,
                text_value,
                None,  # notes
            ))


def analyze_all(conn: psycopg.Connection) -> None:
    """Run ANALYZE on every loaded table.

    Critical for accurate EXPLAIN output. Without this the planner thinks
    the tables are still empty (last seen post-TRUNCATE) and won't choose
    indexes.
    """
    for table in (
        "researchers",
        "projects",
        "project_researchers",
        "samples",
        "experiments",
        "experiment_samples",
        "measurements",
    ):
        conn.execute(f"ANALYZE {table}")


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

    print(f"load_test: bulk loading {plan.measurements:,} measurements (+ supporting rows)...")
    with psycopg.connect(_psycopg_url(load_url)) as conn:
        truncate_all(conn)
        t0 = time.monotonic()
        bulk_load(conn, plan)
        conn.commit()
        load_elapsed = time.monotonic() - t0

        print("load_test: analyzing tables for planner statistics...")
        t0 = time.monotonic()
        analyze_all(conn)
        conn.commit()
        analyze_elapsed = time.monotonic() - t0

    rate = plan.measurements / load_elapsed if load_elapsed > 0 else float("inf")
    print(f"load_test: loaded in {load_elapsed:.1f}s ({rate:,.0f} measurements/sec)")
    print(f"load_test: analyzed in {analyze_elapsed:.2f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
