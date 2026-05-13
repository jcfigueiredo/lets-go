"""Measurement schema constraints — the polymorphic STI discriminator (D3)."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import Measurement, MeasurementKind


# ── Valid kinds ─────────────────────────────────────────────────────────────


def test_numeric_measurement_valid(db: Session, factories):
    m = factories.numeric_measurement(numeric_value=Decimal("98.6"), unit="F")
    db.flush()
    db.refresh(m)
    assert m.kind == MeasurementKind.NUMERIC
    assert m.numeric_value == Decimal("98.6")
    assert m.unit == "F"


def test_categorical_measurement_valid(db: Session, factories):
    m = factories.categorical_measurement(categorical_value="negative")
    db.flush()
    db.refresh(m)
    assert m.kind == MeasurementKind.CATEGORICAL
    assert m.categorical_value == "negative"


def test_text_measurement_valid(db: Session, factories):
    m = factories.text_measurement(text_value="Researcher noted unusual behavior.")
    db.flush()
    db.refresh(m)
    assert m.kind == MeasurementKind.TEXT
    assert m.text_value == "Researcher noted unusual behavior."


# ── CHECK constraint enforcement ────────────────────────────────────────────


def test_numeric_kind_without_unit_rejected(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.numeric_measurement(unit=None)


def test_numeric_kind_without_numeric_value_rejected(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.numeric_measurement(numeric_value=None)


def test_categorical_with_numeric_columns_rejected(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.categorical_measurement(numeric_value=Decimal("1"))


def test_text_with_unit_rejected(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.text_measurement(unit="g")


# ── FK and nullability ─────────────────────────────────────────────────────


def test_sample_id_nullable(db: Session, factories):
    m = factories.numeric_measurement(sample_id=None)
    db.flush()
    db.refresh(m)
    assert m.sample_id is None


def test_recorded_by_required(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.numeric_measurement(recorded_by=None)


def test_invalid_experiment_fk_rejected(db: Session, factories):
    with pytest.raises(IntegrityError):
        factories.numeric_measurement(experiment_id=999_999)


# ── Query ergonomics ───────────────────────────────────────────────────────


def test_query_measurements_for_experiment(db: Session, factories):
    exp = factories.experiment()
    db.flush()
    for _ in range(3):
        factories.numeric_measurement(experiment_id=exp.id)
    db.flush()

    rows = db.exec(
        select(Measurement).where(Measurement.experiment_id == exp.id)
    ).all()
    assert len(rows) == 3
