"""ExperimentSample schema constraints."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import ExperimentSample


def test_create_assignment(db: Session, factories):
    exp = factories.experiment()
    sample = factories.sample()
    db.flush()

    db.add(ExperimentSample(experiment_id=exp.id, sample_id=sample.id))
    db.flush()

    found = db.exec(
        select(ExperimentSample).where(
            ExperimentSample.experiment_id == exp.id,
            ExperimentSample.sample_id == sample.id,
        )
    ).one()
    assert found.assigned_at is not None


def test_composite_pk_prevents_duplicates(db: Session, factories):
    exp = factories.experiment()
    sample = factories.sample()
    db.flush()

    db.add(ExperimentSample(experiment_id=exp.id, sample_id=sample.id))
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ExperimentSample(experiment_id=exp.id, sample_id=sample.id))
        db.flush()


def test_invalid_experiment_fk_rejected(db: Session, factories):
    sample = factories.sample()
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ExperimentSample(experiment_id=999_999, sample_id=sample.id))
        db.flush()


def test_invalid_sample_fk_rejected(db: Session, factories):
    exp = factories.experiment()
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ExperimentSample(experiment_id=exp.id, sample_id=999_999))
        db.flush()


def test_sample_used_across_multiple_experiments(db: Session, factories):
    """The structural reason this aggregate exists: one sample, many experiments."""
    sample = factories.sample()
    exp_a = factories.experiment()
    exp_b = factories.experiment()
    db.flush()

    db.add(ExperimentSample(experiment_id=exp_a.id, sample_id=sample.id))
    db.add(ExperimentSample(experiment_id=exp_b.id, sample_id=sample.id))
    db.flush()

    rows = db.exec(select(ExperimentSample).where(ExperimentSample.sample_id == sample.id)).all()
    assert len(rows) == 2
