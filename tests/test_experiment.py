"""Experiment schema constraints."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import Experiment, ExperimentStatus


def test_create_and_read(db: Session, factories):
    factories.experiment(title="E1")
    db.flush()

    found = db.exec(select(Experiment).where(Experiment.title == "E1")).one()
    assert found.status == ExperimentStatus.PLANNED


def test_status_accepts_each_valid_value(db: Session, factories):
    for status in ExperimentStatus:
        factories.experiment(status=status)
    db.flush()

    rows = db.exec(select(Experiment)).all()
    assert len(rows) == len(ExperimentStatus)


def test_date_order_check_rejects_end_before_start(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.experiment(start_date=date(2026, 6, 1), end_date=date(2026, 5, 1))


def test_date_order_check_allows_null_dates(db: Session, factories):
    factories.experiment(start_date=None, end_date=None)
    factories.experiment(start_date=date(2026, 1, 1), end_date=None)
    factories.experiment(start_date=None, end_date=date(2026, 12, 31))
    db.flush()  # should not raise


def test_no_self_follow_up_check(db: Session, factories):
    exp = factories.experiment()
    db.flush()
    exp.follows_up_experiment_id = exp.id
    with pytest.raises(IntegrityError):
        db.flush()


def test_follows_up_chain(db: Session, factories):
    first = factories.experiment(title="First study")
    db.flush()
    second = factories.experiment(title="Replication", follows_up_experiment_id=first.id)
    db.flush()

    db.refresh(second)
    assert second.follows_up_experiment_id == first.id


def test_invalid_project_fk_rejected(db: Session):
    bad = Experiment(
        project_id=999_999,
        title="orphan",
        hypothesis="x",
    )
    with pytest.raises(IntegrityError):
        db.add(bad)
        db.flush()
