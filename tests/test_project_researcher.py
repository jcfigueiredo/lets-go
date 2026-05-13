"""ProjectResearcher schema constraints."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import ProjectResearcher


def test_create_membership(db: Session, factories):
    proj = factories.project()
    alice = factories.researcher()
    db.flush()

    db.add(ProjectResearcher(project_id=proj.id, researcher_id=alice.id))
    db.flush()

    found = db.exec(
        select(ProjectResearcher).where(
            ProjectResearcher.project_id == proj.id,
            ProjectResearcher.researcher_id == alice.id,
        )
    ).one()
    assert found.joined_at is not None


def test_composite_pk_prevents_duplicates(db: Session, factories):
    proj = factories.project()
    alice = factories.researcher()
    db.flush()

    db.add(ProjectResearcher(project_id=proj.id, researcher_id=alice.id))
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ProjectResearcher(project_id=proj.id, researcher_id=alice.id))
        db.flush()


def test_invalid_project_fk_rejected(db: Session, factories):
    alice = factories.researcher()
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ProjectResearcher(project_id=999_999, researcher_id=alice.id))
        db.flush()


def test_invalid_researcher_fk_rejected(db: Session, factories):
    proj = factories.project()
    db.flush()

    with pytest.raises(IntegrityError):
        db.add(ProjectResearcher(project_id=proj.id, researcher_id=999_999))
        db.flush()
