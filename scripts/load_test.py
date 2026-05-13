"""Load test for schema validation under volume.

See docs/superpowers/specs/2026-05-13-load-test-design.md for the design.

Runs against a separate ``lab_load`` Postgres database; idempotent (each
invocation truncates and reloads). Outputs a per-query report to stdout.

Usage:
    uv run python -m scripts.load_test --rows 100000
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass


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
    print(f"load_test plan for N={plan.rows:,}:")
    print(f"  researchers:        {plan.researchers:>10,}")
    print(f"  projects:           {plan.projects:>10,}")
    print(f"  memberships:        {plan.memberships:>10,}")
    print(f"  samples:            {plan.samples:>10,}")
    print(f"  experiments:        {plan.experiments:>10,}")
    print(f"  experiment_samples: {plan.experiment_samples:>10,}")
    print(f"  measurements:       {plan.measurements:>10,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
