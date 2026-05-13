"""Seed entry point.

Hand-curated, deterministic data exercising the spec scenarios. Idempotent:
``make seed && make seed`` produces the same final state.

Idempotency strategy: ``INSERT … ON CONFLICT DO NOTHING`` on the natural
identifier (email, accession code, composite PK, etc.). For tables without
a UNIQUE constraint on the seed anchor (e.g. ``projects.title``), use a
check-then-insert pattern.
"""

from datetime import UTC, date, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from lab.db import engine
from lab.models import (
    Experiment,
    ExperimentSample,
    ExperimentStatus,
    Project,
    ProjectResearcher,
    ProjectStatus,
    Researcher,
    ResearcherRole,
    Sample,
)


def _seed_researchers(session: Session) -> None:
    data = [
        {"name": "Alice Tan",   "email": "alice@lab.example",   "role": ResearcherRole.PRINCIPAL_INVESTIGATOR},
        {"name": "Bob Singh",   "email": "bob@lab.example",     "role": ResearcherRole.LAB_TECHNICIAN},
        {"name": "Carol Liu",   "email": "carol@lab.example",   "role": ResearcherRole.GRADUATE_STUDENT},
        {"name": "Diego Cruz",  "email": "diego@lab.example",   "role": ResearcherRole.POSTDOC},
    ]
    stmt = insert(Researcher).values(data).on_conflict_do_nothing(index_elements=["email"])
    session.execute(stmt)


def _seed_projects(session: Session) -> None:
    """Two canonical projects.

    No UNIQUE constraint on ``title`` means we can't use ``ON CONFLICT``; instead
    we check-then-insert, which yields the same idempotency guarantee.
    """
    seeds = [
        {"title": "Glucose Tolerance Study", "description": "Long-term tracking of glucose responses.", "status": ProjectStatus.ACTIVE},
        {"title": "Soil Microbiome Survey",  "description": "Comparative survey across three watersheds.", "status": ProjectStatus.PLANNING},
    ]
    for row in seeds:
        existing = session.exec(select(Project).where(Project.title == row["title"])).first()
        if existing is None:
            session.add(Project(**row))


def _seed_memberships(session: Session) -> None:
    """Assign researchers to projects.

    Satisfies the multi-researcher spec scenario: Glucose Tolerance Study gets
    Alice (PI), Bob (technician), Carol (grad student). Soil Microbiome Survey
    gets Alice as a single-researcher control case.

    Idempotent via ``INSERT … ON CONFLICT DO NOTHING`` anchored explicitly on
    the composite PK columns — robust against any future UNIQUE constraint
    additions that would otherwise change the default conflict target.
    """
    session.flush()  # ensure researchers + projects have IDs

    glucose = session.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    soil = session.exec(select(Project).where(Project.title == "Soil Microbiome Survey")).one()
    alice = session.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    bob = session.exec(select(Researcher).where(Researcher.email == "bob@lab.example")).one()
    carol = session.exec(select(Researcher).where(Researcher.email == "carol@lab.example")).one()

    memberships = [
        {"project_id": glucose.id, "researcher_id": alice.id},
        {"project_id": glucose.id, "researcher_id": bob.id},
        {"project_id": glucose.id, "researcher_id": carol.id},
        {"project_id": soil.id,    "researcher_id": alice.id},
    ]
    stmt = insert(ProjectResearcher).values(memberships).on_conflict_do_nothing(
        index_elements=["project_id", "researcher_id"]
    )
    session.execute(stmt)


def _seed_samples(session: Session) -> None:
    """Three canonical samples (two blood + one soil) covering both projects.

    Idempotent via ``INSERT … ON CONFLICT DO NOTHING`` anchored on the UNIQUE
    ``accession_code`` column.
    """
    data = [
        {"accession_code": "GTS-001", "specimen_type": "blood", "collected_at": datetime(2026, 1, 15, tzinfo=UTC), "storage_location": "Freezer A / Shelf 1"},
        {"accession_code": "GTS-002", "specimen_type": "blood", "collected_at": datetime(2026, 2, 10, tzinfo=UTC), "storage_location": "Freezer A / Shelf 1"},
        {"accession_code": "SMS-001", "specimen_type": "soil",  "collected_at": datetime(2026, 3, 1,  tzinfo=UTC), "storage_location": "Cabinet 4 / Bin 7"},
    ]
    stmt = insert(Sample).values(data).on_conflict_do_nothing(index_elements=["accession_code"])
    session.execute(stmt)


def _seed_experiments(session: Session) -> None:
    """Three experiments — one of them follows up another.

    Satisfies the spec scenario "experiments that reference earlier experiments":
    the follow-up OGTT replication references the baseline OGTT.

    Idempotent via check-then-insert on (project_id, title), since there is no
    UNIQUE constraint. ``follows_up_experiment_id`` is set after the baseline
    experiment exists in the session.
    """
    session.flush()  # ensure projects have IDs

    glucose = session.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    soil = session.exec(select(Project).where(Project.title == "Soil Microbiome Survey")).one()

    # Phase 1: experiments with no follow-up reference.
    phase_1 = [
        {
            "project_id": glucose.id,
            "title": "Baseline OGTT",
            "hypothesis": "Baseline response distribution.",
            "start_date": date(2026, 1, 20),
            "end_date": date(2026, 1, 25),
            "status": ExperimentStatus.COMPLETED,
        },
        {
            "project_id": soil.id,
            "title": "Watershed A 16S",
            "hypothesis": "Diverse microbial communities.",
            "start_date": date(2026, 3, 5),
            "end_date": None,
            "status": ExperimentStatus.RUNNING,
        },
    ]
    for row in phase_1:
        existing = session.exec(
            select(Experiment).where(
                Experiment.project_id == row["project_id"],
                Experiment.title == row["title"],
            )
        ).first()
        if existing is None:
            session.add(Experiment(**row))
    session.flush()

    # Phase 2: follow-up references baseline. The flush above guarantees the
    # baseline row has an ID before we wire the FK.
    baseline = session.exec(
        select(Experiment).where(Experiment.title == "Baseline OGTT")
    ).one()
    follow_up = {
        "project_id": glucose.id,
        "title": "Follow-up OGTT replication",
        "hypothesis": "Replication of baseline distribution with stricter protocol.",
        "start_date": date(2026, 2, 15),
        "end_date": None,
        "status": ExperimentStatus.RUNNING,
        "follows_up_experiment_id": baseline.id,
    }
    existing = session.exec(
        select(Experiment).where(
            Experiment.project_id == follow_up["project_id"],
            Experiment.title == follow_up["title"],
        )
    ).first()
    if existing is None:
        session.add(Experiment(**follow_up))


def _seed_experiment_samples(session: Session) -> None:
    """Assign samples to experiments. Sample GTS-001 is used in both the baseline
    and follow-up OGTT experiments — satisfies the spec scenario "samples used
    across multiple experiments".

    Idempotent via ``INSERT … ON CONFLICT DO NOTHING`` anchored on the composite PK.
    """
    session.flush()

    baseline = session.exec(
        select(Experiment).where(Experiment.title == "Baseline OGTT")
    ).one()
    follow_up = session.exec(
        select(Experiment).where(Experiment.title == "Follow-up OGTT replication")
    ).one()
    watershed = session.exec(
        select(Experiment).where(Experiment.title == "Watershed A 16S")
    ).one()

    gts1 = session.exec(select(Sample).where(Sample.accession_code == "GTS-001")).one()
    gts2 = session.exec(select(Sample).where(Sample.accession_code == "GTS-002")).one()
    sms1 = session.exec(select(Sample).where(Sample.accession_code == "SMS-001")).one()

    rows = [
        {"experiment_id": baseline.id,  "sample_id": gts1.id},
        {"experiment_id": baseline.id,  "sample_id": gts2.id},
        {"experiment_id": follow_up.id, "sample_id": gts1.id},  # GTS-001 reused
        {"experiment_id": watershed.id, "sample_id": sms1.id},
    ]
    stmt = insert(ExperimentSample).values(rows).on_conflict_do_nothing(
        index_elements=["experiment_id", "sample_id"]
    )
    session.execute(stmt)


def seed(session: Session) -> None:
    """Apply seed data idempotently."""
    _seed_researchers(session)
    _seed_projects(session)
    _seed_memberships(session)
    _seed_samples(session)
    _seed_experiments(session)
    _seed_experiment_samples(session)


if __name__ == "__main__":  # pragma: no cover
    with Session(engine) as session:
        seed(session)
        session.commit()
