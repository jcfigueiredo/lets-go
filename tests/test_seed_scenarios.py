"""End-to-end assertions that seed satisfies all four spec-required scenarios.

The spec (lab-experiment-tracking-system.md) requires seed data covering:
1. At least one project with multiple researchers
2. Experiments that reference earlier experiments
3. Samples used across multiple experiments
4. Measurements of more than one kind

These tests are the coherent exhibit — running them proves the seed satisfies
the spec's deliverable requirements end-to-end. Individual seed contribution
tests (in test_seed.py) verify each contribution in isolation; this file
verifies the full picture.
"""

from sqlmodel import Session, func, select

from lab.models import (
    Experiment,
    ExperimentSample,
    Measurement,
    ProjectResearcher,
)
from lab.seed import seed


def test_scenario_1_project_with_multiple_researchers(db: Session):
    """Spec scenario 1: at least one project with multiple researchers."""
    seed(db)
    db.flush()

    counts = db.exec(
        select(ProjectResearcher.project_id, func.count())
        .group_by(ProjectResearcher.project_id)
    ).all()
    assert any(count >= 2 for _, count in counts), (
        "Expected at least one project with ≥2 researchers"
    )


def test_scenario_2_experiment_referencing_earlier(db: Session):
    """Spec scenario 2: experiments that reference earlier experiments."""
    seed(db)
    db.flush()

    follow_ups = db.exec(
        select(Experiment).where(Experiment.follows_up_experiment_id.is_not(None))
    ).all()
    assert len(follow_ups) >= 1, "Expected at least one follow-up experiment"


def test_scenario_3_sample_used_across_multiple_experiments(db: Session):
    """Spec scenario 3: samples used across multiple experiments."""
    seed(db)
    db.flush()

    counts = db.exec(
        select(ExperimentSample.sample_id, func.count())
        .group_by(ExperimentSample.sample_id)
    ).all()
    assert any(count >= 2 for _, count in counts), (
        "Expected at least one sample used in ≥2 experiments"
    )


def test_scenario_4_measurements_of_multiple_kinds(db: Session):
    """Spec scenario 4: measurements of more than one kind."""
    seed(db)
    db.flush()

    kinds = db.exec(select(Measurement.kind).group_by(Measurement.kind)).all()
    assert len(kinds) >= 2, "Expected measurements of ≥2 kinds"
