from sqlmodel import Session, func, select

from lab.models import (
    Experiment,
    ExperimentSample,
    Measurement,
    MeasurementKind,
    Project,
    ProjectResearcher,
    Researcher,
    Sample,
)
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
        select(ProjectResearcher.project_id, func.count()).group_by(ProjectResearcher.project_id)
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
        select(ExperimentSample.sample_id, func.count()).group_by(ExperimentSample.sample_id)
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


def test_seed_creates_measurements(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Measurement)).one()
    assert count == 4


def test_seed_satisfies_multi_kind_scenario(db: Session):
    """Spec scenario: measurements of more than one kind."""
    seed(db)
    db.flush()

    kinds = db.exec(select(Measurement.kind).group_by(Measurement.kind)).all()
    assert len(kinds) >= 2


def test_seed_is_idempotent(db: Session):
    """Idempotency: re-running seed must not change row counts AND must not overwrite existing rows.

    Asserts mutation survival for all three idempotency strategies across all seven aggregates:
    - ``ON CONFLICT DO NOTHING`` on a UNIQUE column (researchers, samples)
    - ``ON CONFLICT DO NOTHING`` on composite PK (memberships, experiment-samples)
    - check-then-insert in Python (projects, experiments, measurements)
    """
    seed(db)
    db.flush()
    r1 = db.exec(select(func.count()).select_from(Researcher)).one()
    p1 = db.exec(select(func.count()).select_from(Project)).one()
    m1 = db.exec(select(func.count()).select_from(ProjectResearcher)).one()
    s1 = db.exec(select(func.count()).select_from(Sample)).one()
    e1 = db.exec(select(func.count()).select_from(Experiment)).one()
    es1 = db.exec(select(func.count()).select_from(ExperimentSample)).one()
    me1 = db.exec(select(func.count()).select_from(Measurement)).one()

    # Mutate one of each kind; if seed accidentally upserts, mutations revert.
    alice = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    alice.name = "Alice Tan (renamed)"
    glucose = db.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    glucose.description = "Mutated description"
    # Memberships and experiment-samples have no naturally-mutable columns —
    # capture their server-stamped timestamps and assert they don't get re-stamped.
    alice_glucose = db.exec(
        select(ProjectResearcher).where(
            ProjectResearcher.project_id == glucose.id,
            ProjectResearcher.researcher_id == alice.id,
        )
    ).one()
    alice_glucose_joined_at = alice_glucose.joined_at
    gts1 = db.exec(select(Sample).where(Sample.accession_code == "GTS-001")).one()
    gts1.storage_location = "Mutated freezer location"
    baseline = db.exec(select(Experiment).where(Experiment.title == "Baseline OGTT")).one()
    baseline.hypothesis = "Mutated hypothesis text"
    baseline_gts1 = db.exec(
        select(ExperimentSample).where(
            ExperimentSample.experiment_id == baseline.id,
            ExperimentSample.sample_id == gts1.id,
        )
    ).one()
    baseline_gts1_assigned_at = baseline_gts1.assigned_at
    glucose_reading = db.exec(
        select(Measurement).where(
            Measurement.kind == MeasurementKind.NUMERIC,
            Measurement.experiment_id == baseline.id,
        )
    ).first()
    glucose_reading.notes = "Mutated note on a glucose reading"
    db.flush()

    seed(db)
    db.flush()
    r2 = db.exec(select(func.count()).select_from(Researcher)).one()
    p2 = db.exec(select(func.count()).select_from(Project)).one()
    m2 = db.exec(select(func.count()).select_from(ProjectResearcher)).one()
    s2 = db.exec(select(func.count()).select_from(Sample)).one()
    e2 = db.exec(select(func.count()).select_from(Experiment)).one()
    es2 = db.exec(select(func.count()).select_from(ExperimentSample)).one()
    me2 = db.exec(select(func.count()).select_from(Measurement)).one()
    alice_after = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    glucose_after = db.exec(select(Project).where(Project.title == "Glucose Tolerance Study")).one()
    alice_glucose_after = db.exec(
        select(ProjectResearcher).where(
            ProjectResearcher.project_id == glucose.id,
            ProjectResearcher.researcher_id == alice.id,
        )
    ).one()
    gts1_after = db.exec(select(Sample).where(Sample.accession_code == "GTS-001")).one()
    baseline_after = db.exec(select(Experiment).where(Experiment.title == "Baseline OGTT")).one()
    baseline_gts1_after = db.exec(
        select(ExperimentSample).where(
            ExperimentSample.experiment_id == baseline.id,
            ExperimentSample.sample_id == gts1.id,
        )
    ).one()
    glucose_reading_after = db.exec(
        select(Measurement).where(Measurement.id == glucose_reading.id)
    ).one()

    assert (r1, p1, m1, s1, e1, es1, me1) == (r2, p2, m2, s2, e2, es2, me2) == (4, 2, 4, 3, 3, 4, 4)
    assert alice_after.name == "Alice Tan (renamed)", "Seed must not overwrite existing researchers"
    assert glucose_after.description == "Mutated description", (
        "Seed must not overwrite existing projects"
    )
    assert alice_glucose_after.joined_at == alice_glucose_joined_at, (
        "Seed must not re-stamp membership joined_at"
    )
    assert gts1_after.storage_location == "Mutated freezer location", (
        "Seed must not overwrite existing samples"
    )
    assert baseline_after.hypothesis == "Mutated hypothesis text", (
        "Seed must not overwrite existing experiments"
    )
    assert baseline_gts1_after.assigned_at == baseline_gts1_assigned_at, (
        "Seed must not re-stamp experiment-sample assigned_at"
    )
    assert glucose_reading_after.notes == "Mutated note on a glucose reading", (
        "Seed must not overwrite existing measurements"
    )
