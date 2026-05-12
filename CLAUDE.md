# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This is a **greenfield take-home exercise**. As of this writing the repo contains only the spec (`lab-experiment-tracking-system.txt`) — no source code, no migrations, no Docker config, no README. There are no build/test/lint commands to document yet; add them here once the toolchain is chosen.

## What this project is

A data model for a **laboratory experiment tracking system**, delivered as Postgres migrations + Docker + seed data. The full brief is in `lab-experiment-tracking-system.txt`; read it before designing anything. Key entities and the relationships that drive the schema:

- **Researchers** ↔ **Projects**: many-to-many (researchers collaborate on multiple projects; projects have multiple researchers). Roles (PI, lab tech, grad student, …) are tracked per researcher — open question whether role is global or per-project.
- **Projects** → **Experiments**: one-to-many. Every experiment belongs to **exactly one** project.
- **Experiments** ↔ **Samples**: many-to-many (a sample can be used across experiments; an experiment uses multiple samples).
- **Experiments** → **Experiments**: self-reference for follow-ups (replication, iteration, refined hypothesis).
- **Measurements** → **Experiment** (required) + **Sample** (usually, not always). Measurements are **polymorphic**: numeric-with-unit, categorical, or free-text. "New kinds of measurements are added occasionally" — the schema must accommodate new measurement types without migrations to add columns per type. This is the single most interesting design decision in the model.
- Both Projects and Experiments have **lifecycle status** (planning/active/completed/cancelled for projects; experiments have their own status). Decide whether to share an enum or keep them separate.

## Required deliverables (from the spec)

1. **Single-command bootstrap**: `git clone` → run one documented command → running Postgres with schema + seed data. This command must be in the README.
2. **Seed data that exercises the interesting parts** — at minimum: one project with multiple researchers, an experiment that references an earlier experiment, a sample used across multiple experiments, and measurements of more than one kind.
3. **README** must cover: (a) the one-command bootstrap, (b) assumptions made about ambiguities, (c) tradeoffs including **at least one thing deliberately not done**, (d) open questions for the lab.

## How to approach work here

The spec explicitly says: *"We'd much rather see a decisive model built on explicit assumptions than a hesitant one that hedges against every possibility."* This shapes how to make decisions in this repo:

- **Decide and document, don't hedge.** When the spec is ambiguous (e.g., is researcher role global or per-project? can a measurement exist without a sample? are sample types an enum or free-text?), pick a defensible answer and write the assumption into the README. Don't add columns "just in case."
- **The interview extends this live.** Choices will be defended and modified in a follow-up session, so favor designs that are easy to *explain* over designs that are clever. Avoid premature normalization or abstraction that you can't justify in one sentence.
- **Measurement polymorphism is the load-bearing design call.** Common options: single table with nullable typed columns; single table + JSONB value; table-per-type with a parent; EAV. Each has different ergonomics for adding a new measurement kind later — pick one and be ready to defend the tradeoff in the README's "tradeoffs" section.

## When this file should be updated

Once the toolchain lands (migration tool, Docker setup, language choice for any tooling scripts), replace this section with the actual commands:

- How to start the database (the one-command bootstrap)
- How to run migrations up/down
- How to reset and re-seed
- How to run a single test, once tests exist

Until then, don't invent commands here.
