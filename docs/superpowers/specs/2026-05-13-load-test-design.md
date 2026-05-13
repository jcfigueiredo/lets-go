# Load Test Design — Schema Validation Under Volume

**Status:** Approved (pending sign-off on this written form)
**Date:** 2026-05-13
**Author:** Claudio + Claude
**Scope:** Standalone load test that bulk-loads the schema to a configurable row count, runs `EXPLAIN ANALYZE` against one query per declared index, and reports which indexes the planner actually uses.

## Goal

Validate that the schema's 10 non-PK indexes are used by the Postgres planner under volume. Output a per-query report showing the plan and execution timing, with a ✓/✗ verdict against the index that query is *supposed* to exercise.

This is **schema validation under volume**, not a throughput benchmark, soak test, or concurrent-client simulator. The output is interview-defense ammo: "I tested every index choice at N rows; here are the verdicts."

## Scope

### In

- A standalone Python script at `scripts/load_test.py`
- A separate Postgres database `lab_load` (created on demand)
- Postgres `COPY` via `psycopg.cursor.copy(...)` for the bulk insert path
- `ANALYZE` after the load so the planner has accurate statistics
- 10 `EXPLAIN ANALYZE` queries (one per non-PK index)
- Stdout report with per-query verdict + a summary line
- `make load [N=…]` Makefile target

### Deliberately out

- Throughput benchmark (rows/sec, queries/sec)
- Soak / endurance testing
- Concurrent-client simulation
- Query latency under write contention
- Warm-up passes (we want honest cold-cache numbers; re-run for warm-cache comparison)
- VACUUM (TRUNCATE + ANALYZE is sufficient — no dead tuples to reclaim)
- A `make load-clean` target (YAGNI — each `make load` is idempotent via TRUNCATE)
- Writing the report to a file (pipe to `tee` if needed)

## Mechanism

The script is the single orchestrator. End-to-end on each `make load`:

1. **Ensure `lab_load` database exists.** `CREATE DATABASE lab_load` against `postgres` system DB; idempotent (`IF NOT EXISTS` or swallow the duplicate-DB error).
2. **Apply migrations** via `alembic upgrade head` against `lab_load`. Idempotent (alembic tracks revisions via `alembic_version`).
3. **TRUNCATE all data tables** in dependency order (measurements → experiment_samples → experiments → samples → project_researchers → projects → researchers). `TRUNCATE … RESTART IDENTITY CASCADE` resets sequences too.
4. **Bulk-insert `N` measurements + proportional supporting rows** via `psycopg.cursor.copy(...)`. Proportions (default `N=100_000`):
   - Researchers: `max(N // 50_000, 4)` (default 4) — small, but enough for FK variety
   - Projects: `max(N // 20_000, 5)` (default 5)
   - Project-Researcher memberships: `min(researchers * projects, N // 5_000)` (default 20)
   - Samples: `max(N // 5_000, 20)` (default 20)
   - Experiments: `max(N // 10_000, 10)` (default 10) — including some follow-up references for query 5
   - Experiment-Sample assignments: `max(N // 2_500, 40)` (default 40)
   - Measurements: `N` (the headline number)
5. **Run `ANALYZE`** on every loaded table. Without this the planner thinks the table is empty and won't use indexes.
6. **Execute 10 `EXPLAIN (ANALYZE, BUFFERS) <query>`** statements. Parse the top node type from each plan. Compare against the expected index.
7. **Print a report.** Per-query block + summary line.

## The 10 benchmark queries

Each query is hand-tuned to exercise exactly one non-PK index. Variables (e.g., `<some_researcher_id>`) are picked at runtime from the loaded data — usually the first inserted ID, so they're guaranteed to match rows and produce meaningful plans.

| # | Index | SQL gist |
|---|---|---|
| 1 | `uq_researchers_email` | `SELECT * FROM researchers WHERE email = $1` |
| 2 | `uq_samples_accession_code` | `SELECT * FROM samples WHERE accession_code = $1` |
| 3 | `ix_project_researchers_researcher_id` | `SELECT p.title FROM projects p JOIN project_researchers pr ON pr.project_id = p.id WHERE pr.researcher_id = $1` (reverse-direction join — composite PK doesn't cover this) |
| 4 | `ix_experiments_project_id` | `SELECT * FROM experiments WHERE project_id = $1` |
| 5 | `ix_experiments_follows_up_experiment_id` | `SELECT * FROM experiments WHERE follows_up_experiment_id = $1` |
| 6 | `ix_experiment_samples_sample_id` | `SELECT e.title FROM experiments e JOIN experiment_samples es ON es.experiment_id = e.id WHERE es.sample_id = $1` (reverse direction) |
| 7 | `ix_measurements_experiment_id_recorded_at` | `SELECT * FROM measurements WHERE experiment_id = $1 ORDER BY recorded_at DESC LIMIT 100` (proves the composite serves both filter AND sort — plan should have **no** Sort node above the Index Scan) |
| 8 | `ix_measurements_sample_id` | `SELECT count(*) FROM measurements WHERE sample_id = $1` |
| 9 | `ix_measurements_recorded_by` | `SELECT count(*) FROM measurements WHERE recorded_by = $1` |
| 10 | `ix_measurements_kind` | `SELECT count(*) FROM measurements WHERE kind = 'numeric' AND unit = 'mg/dL' AND numeric_value > 100` (compound predicate; pure `kind = 'numeric'` may seq-scan due to low cardinality — three kinds means ~33% match) |

## Output format

One block per query, then a summary line. Approximate shape:

```
============================================================
Load test report — N=100,000 measurements
Database: lab_load on localhost:54321
Load time: 12.4s (8,065 rows/sec)
Analyze time: 0.18s
============================================================

[1/10] Lookup researcher by email
       Index expected: uq_researchers_email
       SQL: SELECT * FROM researchers WHERE email = $1
       Plan: Index Scan using uq_researchers_email on researchers
         (cost=0.28..8.30 rows=1 width=...)
       Execution time: 0.082 ms
       Verdict: ✓ used expected index

[2/10] Lookup sample by accession code
       Index expected: uq_samples_accession_code
       SQL: SELECT * FROM samples WHERE accession_code = $1
       Plan: Index Scan using uq_samples_accession_code on samples
       Execution time: 0.071 ms
       Verdict: ✓ used expected index

…

[7/10] Recent measurements for an experiment (filter + order)
       Index expected: ix_measurements_experiment_id_recorded_at
       SQL: SELECT * FROM measurements WHERE experiment_id = $1
            ORDER BY recorded_at DESC LIMIT 100
       Plan: Limit -> Index Scan Backward using
             ix_measurements_experiment_id_recorded_at on measurements
       Execution time: 0.412 ms
       Verdict: ✓ used expected index (no Sort node — composite serves order)

…

============================================================
Verdicts: 10/10 used expected index
============================================================
```

Verdict logic:
- ✓ — top-level node beneath any filter/sort/aggregate is an `Index Scan` (or `Index Only Scan`) using the **expected** index.
- ✗ — anything else (Seq Scan, Bitmap Index Scan over a wrong index, Index Scan over a wrong index).

For query 7 specifically, also verify there's no `Sort` node above the Index Scan (proves the composite serves the `ORDER BY` for free).

## Target database

`lab_load`, separate from `lab` (dev) and `lab_test` (pytest). Reasons:

- The load test fills the DB with ~100k rows by default; dev `lab` should stay small (the 17 seeded rows) for live psql exploration.
- `lab_test` is wiped per-test via SAVEPOINT rollback; it would conflict with a single-shot load.
- A separate DB makes the load test cheap to nuke independently of dev work.

Created idempotently. Schema is brought up via the same Alembic migrations the other databases use.

## Makefile surface

One target:

```makefile
load: ## Run DB load test; default N=100000. Override: make load N=1000000
	uv run python -m scripts.load_test --rows $${N:-100000}
```

The script accepts `--rows` (default 100,000). No `--seed` flag — each run uses fresh random data. If deterministic runs become valuable (e.g., for comparing two schema variants), add `--seed` then; YAGNI now.

## Open design calls (resolved here)

1. **Standalone script vs pytest marker vs library module.** Standalone script. Load tests produce reports; pytest is for assertions. Putting it under `src/lab/` couples ops tooling to the runtime library and forces the 100% coverage gate. `scripts/` is the standard home.
2. **Cold cache only, no warm-up.** Reviewer sees honest first-run numbers. Re-run for warm-cache comparison.
3. **TRUNCATE + ANALYZE, no VACUUM.** TRUNCATE leaves zero dead tuples; ANALYZE is what updates planner stats. VACUUM would be empty work.
4. **No `make load-clean` target.** Each `make load` truncates; the script is idempotent. Drop the DB manually if needed.
5. **No `--report-file` flag.** Stdout only. Pipe to `tee` if a file is wanted.
6. **Hardcoded list of 10 expected indexes.** Could be discovered via `pg_indexes` but hardcoded is clearer ("here's exactly what I'm validating").
7. **Compound predicates for low-cardinality columns.** Query 10 uses `kind = 'numeric' AND unit = 'mg/dL' AND numeric_value > 100` rather than bare `kind = 'numeric'`, because at ~33% match the planner correctly chooses seq scan; compound gives it a reason to start with the index.

## Coverage exclusion

`scripts/load_test.py` lives outside `src/lab/`, so the existing `[tool.coverage.run] source = ["src/lab"]` configuration already excludes it. No new pragma or config knob needed.

Worth a one-line note in CLAUDE.md's anti-patterns: *"Operational scripts live under `scripts/`, not `src/lab/`. Coverage source = `src/lab` deliberately omits them — load/benchmark tools are programs, not unit-tested behavior."*

## What this does NOT decide

These are deliberately deferred:

- The exact data shape of generated measurements — `numeric_value` distributions, unit variety, categorical/text mix. The implementation plan picks defaults; revisit if planner choices look unrealistic.
- Whether to add tests for the load script itself. Probably no — the script's correctness is judged by its report. If the report looks wrong, the script gets fixed.
- Whether to wire `make start` to also run a smoke load. No — `make start` should remain bootstrap-only.
- Whether to record runs over time (regression detection). Out of scope; this is interview-defense ammo, not a CI gate.

## Future enhancements (worth capturing)

To add to `docs/future-enhancements.md` after implementation:

- **Enhancement H — Comparative load test.** Re-run after schema changes; diff verdicts. Catches the "added a column, accidentally invalidated an index" failure mode.
- **Enhancement I — Concurrent client simulation.** `locust` or `pgbench` script that simulates N researchers querying simultaneously. Validates index choices under contention (locking, lock waits).
- **Enhancement J — `track_io_timing` for I/O-vs-CPU breakdown.** Postgres config knob; if enabled, EXPLAIN reports separate I/O time.
- **Enhancement K — Index-only scan validation.** Some queries should achieve "Index Only Scan" (no heap fetches). Validate that the visibility map / covering indexes are doing their job.
