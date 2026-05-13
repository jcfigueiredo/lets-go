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

    print(f"load_test: would load {args.rows:,} measurements")
    print("load_test: (no-op for now — implementation lands in subsequent tasks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
