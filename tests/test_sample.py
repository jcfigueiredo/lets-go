"""Sample schema constraints."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import Sample


def test_create_and_read(db: Session, factories):
    factories.sample(accession_code="ACC-1", specimen_type="tissue")
    db.flush()

    found = db.exec(select(Sample).where(Sample.accession_code == "ACC-1")).one()
    assert found.specimen_type == "tissue"


def test_accession_code_is_unique(db: Session, factories):
    factories.sample(accession_code="DUP-1")
    db.flush()

    with pytest.raises(IntegrityError):
        factories.sample(accession_code="DUP-1")


def test_accession_code_is_required(db: Session):
    bad = Sample(
        accession_code=None,
        specimen_type="x",
        collected_at=datetime.now(UTC),
        storage_location="here",
    )
    with pytest.raises(IntegrityError):
        db.add(bad)
        db.flush()


def test_specimen_type_is_required(db: Session):
    bad = Sample(
        accession_code="REQ-1",
        specimen_type=None,
        collected_at=datetime.now(UTC),
        storage_location="here",
    )
    with pytest.raises(IntegrityError):
        db.add(bad)
        db.flush()


def test_storage_location_is_required(db: Session):
    bad = Sample(
        accession_code="REQ-2",
        specimen_type="x",
        collected_at=datetime.now(UTC),
        storage_location=None,
    )
    with pytest.raises(IntegrityError):
        db.add(bad)
        db.flush()
