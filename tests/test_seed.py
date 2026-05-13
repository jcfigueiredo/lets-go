from sqlmodel import Session, select, func

from lab.models import Experiment, ExperimentSample, Project, ProjectResearcher, Researcher, Sample
from lab.seed import seed


def test_seed_runs_against_a_session_without_error(db: Session):
    seed(db)
    assert db.is_active


def test_seed_creates_researchers(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Researcher)).one()
    assert count == 4


def test_seed_creates_projects(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Project)).one()
    assert count == 2


def test_seed_creates_memberships(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(ProjectResearcher)).one()
    assert count == 4


def test_seed_creates_samples(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Sample)).one()
    assert count == 3


def test_seed_creates_experiments(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Experiment)).one()
    assert count == 3


def test_seed_satisfies_multi_researcher_scenario(db: Session):
    """Spec scenario: at least one project with multiple researchers."""
    seed(db)
    db.flush()

    counts = db.exec(
        select(ProjectResearcher.project_id, func.count())
        .group_by(ProjectResearcher.project_id)
    ).all()
    assert any(count >= 2 for _, count in counts)


def test_seed_creates_experiment_samples(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(ExperimentSample)).one()
    assert count == 4


def test_seed_satisfies_cross_experiment_sample_scenario(db: Session):
    """Spec scenario: samples used across multiple experiments."""
    seed(db)
    db.flush()

    counts = db.exec(
        select(ExperimentSample.sample_id, func.count())
        .group_by(ExperimentSample.sample_id)
    ).all()
    assert any(count >= 2 for _, count in counts)


def test_seed_satisfies_follow_up_scenario(db: Session):
    """Spec scenario: experiments that reference earlier experiments."""
    seed(db)
    db.flush()

    follow_ups = db.exec(
        select(Experiment).where(Experiment.follows_up_experiment_id.is_not(None))
    ).all()
    assert len(follow_ups) >= 1


def test_seed_is_idempotent(db: Session):
    """Idempotency: re-running seed must not change row counts AND must not overwrite existing rows.

    Asserts mutation survival for BOTH idempotency strategies: ``ON CONFLICT DO NOTHING``
    (researchers, anchored on UNIQUE email; memberships, anchored on composite PK) and
    check-then-insert (projects, no UNIQUE on title).
    """
    seed(db)
    db.flush()
    r1 = db.exec(select(func.count()).select_from(Researcher)).one()
    p1 = db.exec(select(func.count()).select_from(Project)).one()
    m1 = db.exec(select(func.count()).select_from(ProjectResearcher)).one()
    s1 = db.exec(select(func.count()).select_from(Sample)).one()
    e1 = db.exec(select(func.count()).select_from(Experiment)).one()
    es1 = db.exec(select(func.count()).select_from(ExperimentSample)).one()

    # Mutate one of each kind; if seed accidentally upserts, mutations revert.
    alice = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    alice.name = "Alice Tan (renamed)"
    glucose = db.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    glucose.description = "Mutated description"
    # Memberships have no mutable columns to rename, but `joined_at` is server-stamped —
    # capture it to assert re-seed doesn't re-stamp (which would silently change history).
    alice_glucose = db.exec(
        select(ProjectResearcher).where(
            ProjectResearcher.project_id == glucose.id,
            ProjectResearcher.researcher_id == alice.id,
        )
    ).one()
    alice_glucose_joined_at = alice_glucose.joined_at
    db.flush()

    seed(db)
    db.flush()
    r2 = db.exec(select(func.count()).select_from(Researcher)).one()
    p2 = db.exec(select(func.count()).select_from(Project)).one()
    m2 = db.exec(select(func.count()).select_from(ProjectResearcher)).one()
    s2 = db.exec(select(func.count()).select_from(Sample)).one()
    e2 = db.exec(select(func.count()).select_from(Experiment)).one()
    es2 = db.exec(select(func.count()).select_from(ExperimentSample)).one()
    alice_after = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    glucose_after = db.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    alice_glucose_after = db.exec(
        select(ProjectResearcher).where(
            ProjectResearcher.project_id == glucose.id,
            ProjectResearcher.researcher_id == alice.id,
        )
    ).one()

    assert (r1, p1, m1, s1, e1, es1) == (r2, p2, m2, s2, e2, es2) == (4, 2, 4, 3, 3, 4)
    assert alice_after.name == "Alice Tan (renamed)", "Seed must not overwrite existing researchers"
    assert glucose_after.description == "Mutated description", "Seed must not overwrite existing projects"
    assert alice_glucose_after.joined_at == alice_glucose_joined_at, (
        "Seed must not re-stamp membership joined_at"
    )
