# Schema Design — Lab Experiment Tracking

**Status:** In progress (brainstorming)
**Date:** 2026-05-12
**Context:** Schema follow-up to the [core infra design](./2026-05-12-core-infra-design.md). The infra deferred all schema decisions to this document.

This file grows incrementally as tensions resolve. Each decision captures **what / why / rejected / assumption** in a few lines.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **Researcher** | A scientist who runs experiments. Has identity, contact info, and a role within the lab. |
| **Project** | A research initiative grouping related experiments. Lifecycle: *planning → active → completed*, or *cancelled*. |
| **Experiment** | A single scientific test inside a project. Has a hypothesis, start/end dates, lifecycle status. May follow up an earlier experiment. |
| **Sample** | A physical specimen used in experiments. Unique identifier, specimen type, collection date, storage location. |
| **Measurement** | A data point produced by an experiment. Kinds: numeric-with-unit, categorical, free-text. New kinds appear occasionally. |

## Candidate aggregates

| Aggregate root | Independent lifecycle | Notes |
|---|---|---|
| Researcher | Yes | exists independently of any project |
| Project | Yes | owns its researcher memberships |
| Experiment | Yes | belongs to exactly one project; may reference an earlier experiment |
| Sample | Yes | independent — collected, stored, consumed across many experiments |
| Measurement | Yes (see D1) | references one experiment + optionally one sample |

## Decisions

### D1 — Measurement is its own aggregate

**Decision:** Measurement is a first-class aggregate, not part of Experiment. `experiment_id` FK with `ON DELETE RESTRICT`.

**Why:**
- Volume reality — real labs produce thousands or millions of measurements per experiment; an aggregate "owned by" Experiment would be fiction at scale.
- The lab queries measurements transversally ("all temperature readings in Q3 across projects A, B, C"), not just experiment-by-experiment.
- `ON DELETE RESTRICT` matches how labs actually behave: they archive, they don't delete. Forcing explicit handling of measurements before experiment deletion makes the decision deliberate.

**Rejected:** Measurement as part of the Experiment aggregate (with `ON DELETE CASCADE`). Simpler whiteboard story but ages poorly at scale and makes cross-experiment queries awkward.

**Assumption:** Cross-table invariants ("measurement timestamp ∈ experiment dates", "no measurements after experiment completion") are NOT enforced at the DB level — Postgres CHECK constraints can't span tables. These would be domain-service rules if added later; captured as a future enhancement.

### D2 — Researcher role is lab-global; Membership is a small entity with `joined_at`

**Decision:** Two parts:

- **Role on Researcher** (global to the lab): `researchers.role` enum (PI, lab tech, grad student, …). Same role across every project they're on.
- **Membership shape**: `project_researchers (project_id, researcher_id, joined_at)` with composite PK on `(project_id, researcher_id)`. No surrogate `id`, no `left_at`.

**Why:**
- The spec literally says "roles within the lab" — a lab-global reading is faithful and defensible. If it turns out to be per-project, we move the column onto the membership without restructuring.
- Labs care about *when* someone joined a project (attribution, grant compliance, paper authorship windows) — a plain join table loses that history.
- `left_at` is YAGNI for the take-home — we have no example in the spec of researchers leaving. If a reviewer asks, the extension is one column.

**Rejected:**
- **Per-project role only** — loses the lab-seniority concept that the spec explicitly names ("principal investigators, lab technicians, graduate students").
- **Both global role + per-project role (dual role concepts)** — more expressive, but two competing notions of "role" to defend at the interview. Picks more flexibility than the spec gives us evidence for.
- **Plain join (no `joined_at`)** — saves one column but loses participation history.
- **Full Membership entity with `id` + `joined_at` + `left_at`** — adds state (`left_at`) we have no spec evidence for.

**Assumption:** "Roles within the lab" is a global property of the researcher, not per-project. If the lab corrects us, role moves to `project_researchers` and `researchers.role` is dropped.

**Open question for the lab:** Do researchers ever leave a project before it completes? If so, we need `left_at` and probably an explicit reason.

### D3 — Measurement polymorphism: STI with Postgres ENUM discriminator

**Decision:** Single Table Inheritance — one `measurements` table with typed value columns + a `measurement_kind` ENUM discriminator + a CHECK constraint enforcing the discriminator contract.

```
measurements
  id, experiment_id, sample_id (nullable), recorded_at, recorded_by, notes,
  kind             measurement_kind NOT NULL
  numeric_value    numeric  NULL
  unit             text     NULL
  categorical_value text    NULL
  text_value       text     NULL
  CHECK ((kind = 'numeric'     AND numeric_value IS NOT NULL AND unit IS NOT NULL
                               AND categorical_value IS NULL AND text_value IS NULL)
      OR (kind = 'categorical' AND categorical_value IS NOT NULL
                               AND numeric_value IS NULL AND unit IS NULL AND text_value IS NULL)
      OR (kind = 'text'        AND text_value IS NOT NULL
                               AND numeric_value IS NULL AND unit IS NULL AND categorical_value IS NULL))
```

Adding a new kind = `ALTER TYPE measurement_kind ADD VALUE …` + an `ALTER TABLE` to update the CHECK constraint. Two migration ops; deliberate.

**Why:**
- The spec says new kinds appear "occasionally" — a migration cadence the lab can absorb. Migrations force a code review and a deliberate conversation about what counts as a new kind.
- Invariants belong in the schema. CHECK constraints make "numeric measurements have units" visible in `\d measurements`. JSONB would push that invariant into application code, invisible to anyone reading the DB.
- Vanilla SQL stays trivial. `SELECT avg(numeric_value) FROM measurements WHERE unit = 'mg/dL'` is the interview-demo shape; the JSONB equivalent reads worse.

**Rejected:**
- **JSONB value column** — no-migration extensibility wins if kinds change *often*; the spec's "occasionally" doesn't justify giving up DB-enforced invariants and query readability. If reality is closer to "new kind every sprint," we'd revisit.
- **Class Table Inheritance** (parent + per-kind child tables) — fully typed, but joins required for "give me all measurements" and adding a kind requires a new table. Over-engineered for three kinds.
- **`text` discriminator + CHECK on allowed values** — equivalent invariant but slightly looser typing than Postgres ENUM. ENUM communicates intent better.
- **`measurement_kinds` lookup table (FK)** — adding a kind = `INSERT` (no schema migration). Loses schema-level enumeration of valid kinds; if we're willing to give that up, we should commit to JSONB instead. Halfway-house options don't win here.

**Assumption:** Adding a new kind requires a migration. If the lab tells us kinds change far more often than "occasionally," this is the first thing to revisit (probably toward JSONB).

**Open question for the lab:** What's the actual cadence of new measurement kinds? Per month? Per quarter? Per year?

### D4 — IDs: `bigserial` everywhere; samples carry an additional `accession_code`

**Decision:**
- **Synthetic PK** on every table: `id bigserial PRIMARY KEY`.
- **Samples additionally carry** `accession_code text NOT NULL UNIQUE` — the lab-assigned identifier from the spec ("The lab assigns each sample a unique identifier"). Synthetic ID is the immutable identity; accession code is a value attached to it.

**Why:**
- No public API, no sharding, no federation. UUID is the production-story answer; bigserial is the honest answer here. Captured in future-enhancements as "swap to UUID v7 if this grew up."
- Lab identifier schemes change. Synthetic PK insulates the FK graph from a future "we renumbered all our samples."
- DDD-aligned: identity is internal; accession code is a value the lab sees and types.

**Rejected:**
- **UUID v4 / v7 as PK** — gains we don't need (no external exposure); costs we'd pay (worse B-tree locality for v4; conversion friction).
- **Sample accession code as PK** — couples every FK in the system to a mutable, lab-owned naming scheme.

### D5 — No soft-delete columns; use lifecycle status where the domain has one

**Decision:**
- **No `deleted_at` columns anywhere.** No `is_deleted` flags.
- **Lifecycle status enums** on Project, Experiment, and (none on others).
- **Researcher** has no archival flag. Researchers persist.
- **Sample** has no lifecycle column in this design — see "Rejected" below.
- **FK behavior**: cascade NONE; all FK actions are `ON DELETE RESTRICT`. This forces explicit handling of dependents before deletion and matches the lab's "archive, don't delete" reality.

**Why:**
- The spec describes lifecycle states for Project and Experiment but says nothing about deletion or archival anywhere.
- YAGNI: adding `is_deleted` columns now creates a parallel concept (active vs deleted) the spec doesn't ask for. Lifecycle enums already model "this isn't current anymore" via `cancelled` / `completed`.
- `RESTRICT` everywhere makes the FK graph behave as one consistent thing — no surprise cascades.

**Rejected:**
- **`deleted_at timestamptz` on every aggregate** — would require every query to filter `WHERE deleted_at IS NULL`. The lab doesn't actually delete; status enums carry the meaning.
- **Sample lifecycle enum** (collected → in_use → depleted → disposed) — spec is silent on whether samples get consumed. Adding this presumes a workflow we have no evidence for. Listed as open question.

**Open question for the lab:** Do samples get consumed/depleted/disposed in your workflow? If so, we'd add a `sample_status` enum and possibly a `depleted_at` timestamp.

### D6 — Sample storage location: single free-text column

**Decision:** `samples.storage_location text NOT NULL`. No structured building/room/freezer/shelf hierarchy.

**Why:**
- Labs vary wildly in how they encode storage. Some use a single barcode encoding everything; others use hierarchical paths; others use locker codes. Modeling building→room→freezer→shelf→position presumptively is wrong without seeing the lab's actual scheme.
- A `text` column accepts whatever scheme they use today and can be parsed/migrated later if they want querying.

**Rejected:**
- **Structured columns** (`building`, `room`, `freezer`, `shelf`, `position`) — premature; presumes one organizational shape across all labs.
- **JSONB `storage` column** — adds complexity without buying us anything; if we're going to be schemaless about storage, plain text is easier.
- **FK to a `storage_locations` table** — over-engineered until we know what hierarchies the lab actually has.

**Open question for the lab:** Do you have a structured location scheme we should reflect (building/room/freezer/shelf/box)? Or is your identifier scheme flat?

### D7 — Separate `project_status` and `experiment_status` enums

**Decision:** Two distinct Postgres enums:
- `project_status`: `planning`, `active`, `completed`, `cancelled`
- `experiment_status`: `planned`, `running`, `completed`, `cancelled`

Note the *deliberate* name divergence: `planning` vs `planned`, `active` vs `running`. Reinforces that these are separate lifecycles even if shapes look similar.

**Why:**
- The spec is explicit: "[each experiment has] its own lifecycle status" (line 12). Two lifecycles, two enums.
- Sharing an enum would suggest they're the same conceptual thing, which the spec contradicts.
- Distinct vocabularies prevent accidental cross-application of logic (e.g., a service method that should only handle Project transitions wouldn't accept an Experiment status by mistake).

**Rejected:**
- **Single shared enum** — collapses two domain concepts; misreads the spec.
- **Identical value names across both enums** (e.g., both use `active`) — works, but loses the linguistic cue that these aren't the same lifecycle.

## Final schema

The accumulated decisions yield this schema. SQL shown for clarity; SQLModel classes will mirror it 1:1.

```sql
-- Types
CREATE TYPE researcher_role    AS ENUM ('principal_investigator', 'lab_technician',
                                        'graduate_student', 'postdoc', 'undergraduate');
CREATE TYPE project_status     AS ENUM ('planning', 'active', 'completed', 'cancelled');
CREATE TYPE experiment_status  AS ENUM ('planned',  'running', 'completed', 'cancelled');
CREATE TYPE measurement_kind   AS ENUM ('numeric',  'categorical', 'text');

-- Researchers
CREATE TABLE researchers (
  id          bigserial PRIMARY KEY,
  name        text NOT NULL,
  email       text NOT NULL UNIQUE,
  role        researcher_role NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Projects
CREATE TABLE projects (
  id          bigserial PRIMARY KEY,
  title       text NOT NULL,
  description text NOT NULL,
  status      project_status NOT NULL DEFAULT 'planning',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Project ↔ Researcher (membership, per D2)
CREATE TABLE project_researchers (
  project_id     bigint NOT NULL REFERENCES projects(id)    ON DELETE RESTRICT,
  researcher_id  bigint NOT NULL REFERENCES researchers(id) ON DELETE RESTRICT,
  joined_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, researcher_id)
);

-- Experiments
CREATE TABLE experiments (
  id                        bigserial PRIMARY KEY,
  project_id                bigint NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  title                     text NOT NULL,
  hypothesis                text NOT NULL,
  start_date                date,
  end_date                  date,
  status                    experiment_status NOT NULL DEFAULT 'planned',
  follows_up_experiment_id  bigint REFERENCES experiments(id) ON DELETE RESTRICT,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT experiment_date_order
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
  CONSTRAINT experiment_no_self_follow_up
    CHECK (follows_up_experiment_id IS NULL OR follows_up_experiment_id <> id)
);

-- Samples
CREATE TABLE samples (
  id                bigserial PRIMARY KEY,
  accession_code    text NOT NULL UNIQUE,             -- per D4
  specimen_type     text NOT NULL,                    -- free text; spec's "and so on" wins over enum
  collected_at      timestamptz NOT NULL,
  storage_location  text NOT NULL,                    -- per D6
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- Experiment ↔ Sample (m:n, per spec line 12 & 14)
CREATE TABLE experiment_samples (
  experiment_id  bigint NOT NULL REFERENCES experiments(id) ON DELETE RESTRICT,
  sample_id      bigint NOT NULL REFERENCES samples(id)     ON DELETE RESTRICT,
  assigned_at    timestamptz NOT NULL DEFAULT now(),         -- symmetric with project_researchers.joined_at
  PRIMARY KEY (experiment_id, sample_id)
);

-- Measurements (per D1 + D3)
CREATE TABLE measurements (
  id                 bigserial PRIMARY KEY,
  experiment_id      bigint NOT NULL  REFERENCES experiments(id) ON DELETE RESTRICT,
  sample_id          bigint           REFERENCES samples(id)     ON DELETE RESTRICT,  -- nullable per spec
  recorded_by        bigint NOT NULL  REFERENCES researchers(id) ON DELETE RESTRICT,
  recorded_at        timestamptz NOT NULL,
  kind               measurement_kind NOT NULL,
  numeric_value      numeric,
  unit               text,
  categorical_value  text,
  text_value         text,
  notes              text,
  CONSTRAINT measurement_value_matches_kind CHECK (
    (kind = 'numeric'     AND numeric_value IS NOT NULL AND unit IS NOT NULL
                          AND categorical_value IS NULL AND text_value IS NULL)
 OR (kind = 'categorical' AND categorical_value IS NOT NULL
                          AND numeric_value IS NULL AND unit IS NULL AND text_value IS NULL)
 OR (kind = 'text'        AND text_value IS NOT NULL
                          AND numeric_value IS NULL AND unit IS NULL AND categorical_value IS NULL)
  )
);
```

### Indexes

Postgres auto-indexes PRIMARY KEYs and UNIQUE constraints. FK columns are NOT auto-indexed, so:

```sql
CREATE INDEX ON project_researchers (researcher_id);       -- "which projects is Alice on?"
CREATE INDEX ON experiments (project_id);                  -- "experiments in this project"
CREATE INDEX ON experiments (follows_up_experiment_id);    -- "what follow-ups exist?"
CREATE INDEX ON experiment_samples (sample_id);            -- "experiments using this sample"
CREATE INDEX ON measurements (experiment_id, recorded_at); -- the dominant query shape
CREATE INDEX ON measurements (sample_id);                  -- "all measurements for this sample"
CREATE INDEX ON measurements (recorded_by);                -- "what did Bob record?"
CREATE INDEX ON measurements (kind);                       -- "all numeric readings"
```

### Assumptions roll-up (for the README)

1. Researcher `role` is global to the lab, not per-project (D2).
2. Researchers don't leave a project before it completes — no `left_at` (D2 open question).
3. New measurement kinds are added rarely enough that a migration per kind is acceptable (D3 open question).
4. `specimen_type` is open-ended free text — labs use varied vocabularies the spec doesn't bound (D6-adjacent).
5. Samples don't have a lifecycle in this design — spec is silent (D5 open question).
6. `storage_location` is opaque text — no structured hierarchy modeled (D6 open question).
7. No soft delete. Hard delete is blocked by FK `RESTRICT` where dependents exist (D1, D5).
8. Synthetic `bigserial` IDs everywhere; samples carry both a synthetic `id` and a lab-owned `accession_code` (D4).

### Tradeoffs roll-up (for the README)

1. STI for measurements (D3) — gain: invariants visible, queries trivial; cost: migration to add a kind.
2. RESTRICT-everywhere FK behavior (D1, D5) — gain: deliberate deletion; cost: more work to actually delete anything (correct trade-off for the domain).
3. Single-text `storage_location` (D6) — gain: accepts any scheme; cost: not directly queryable by sub-component.
4. `bigserial` over UUID (D4) — gain: simpler, faster, smaller; cost: not federation-ready (no federation needed here).
5. Free-text `specimen_type` — gain: accepts any specimen vocabulary; cost: typo risk and no enumeration of valid values.

### Open questions for the lab (for the README)

1. Do researchers ever leave a project mid-flight? (D2)
2. What's the actual cadence of new measurement kinds — quarterly? monthly? (D3)
3. Do samples have a consumption lifecycle (in-use → depleted → disposed)? (D5)
4. Is `storage_location` a free-form code or a hierarchical path we should structure? (D6)
5. Are there researchers who serve different roles on different projects? (D2)

### Known schema-level limitations

- **`follows_up_experiment_id` chains can form cycles.** Single-row CHECK can prevent `id = follows_up_experiment_id` (self-reference), but A→B→A or longer cycles can't be caught at the row level. This is a domain-service concern if cycle prevention matters. Captured for future enhancement.

## Open tensions

(none — design complete)

## Notes

- "Usually references the sample" (spec line 16) → measurement.sample_id is **nullable**. Ambient/equipment/calibration measurements with no specific sample are valid.
- "New kinds of measurements are added occasionally" (spec line 16) → load-bearing for T3.
- "Roles within the lab" (spec line 8) — global vs per-project ambiguity feeds T2.
