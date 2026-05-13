"""Representative read-path queries.

These document the dominant access patterns the lab will use against the schema
and double as interview-extension fodder — each query is a one-liner SQL
exercise that a reviewer might propose mid-interview.
"""

from decimal import Decimal

from sqlmodel import Session, func, select

from lab.models import (
    Experiment,
    Measurement,
    MeasurementKind,
    Project,
    ProjectResearcher,
    Researcher,
)
from lab.seed import seed


def test_measurements_for_project_grouped_by_experiment(db: Session):
    """For each experiment in a project, count its measurements."""
    seed(db)
    db.flush()

    rows = db.exec(
        select(Experiment.title, func.count(Measurement.id))
        .join(Measurement, Measurement.experiment_id == Experiment.id, isouter=True)
        .join(Project, Project.id == Experiment.project_id)
        .where(Project.title == "Glucose Tolerance Study")
        .group_by(Experiment.id, Experiment.title)
        .order_by(Experiment.title)
    ).all()

    titled = dict(rows)
    # Baseline OGTT has 3 measurements (2 numeric + 1 categorical); follow-up has 0.
    assert titled.get("Baseline OGTT", 0) >= 3


def test_numeric_measurements_above_threshold(db: Session):
    """Find all numeric measurements above 100 mg/dL."""
    seed(db)
    db.flush()

    high = db.exec(
        select(Measurement).where(
            Measurement.kind == MeasurementKind.NUMERIC,
            Measurement.unit == "mg/dL",
            Measurement.numeric_value > Decimal("100"),
        )
    ).all()
    # Seed includes a 142.7 mg/dL post-glucose reading.
    assert len(high) >= 1


def test_researchers_on_project(db: Session):
    """Who's on the Glucose Tolerance Study?"""
    seed(db)
    db.flush()

    names = db.exec(
        select(Researcher.name)
        .join(ProjectResearcher, ProjectResearcher.researcher_id == Researcher.id)
        .join(Project, Project.id == ProjectResearcher.project_id)
        .where(Project.title == "Glucose Tolerance Study")
        .order_by(Researcher.name)
    ).all()
    assert "Alice Tan" in names
    assert len(names) >= 2


def test_follow_up_chain(db: Session):
    """Find experiments that have a follow-up (any one another experiment refers back to)."""
    seed(db)
    db.flush()

    chains = db.exec(
        select(Experiment.title)
        .where(
            Experiment.id.in_(
                select(Experiment.follows_up_experiment_id)
                .where(Experiment.follows_up_experiment_id.is_not(None))
            )
        )
    ).all()
    # The baseline OGTT is followed up by the replication experiment.
    assert "Baseline OGTT" in chains
