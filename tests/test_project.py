import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import Project, ProjectStatus


def test_create_and_read(db: Session, factories):
    factories.project(title="P1", description="Pilot study")
    db.flush()

    found = db.exec(select(Project).where(Project.title == "P1")).one()
    assert found.description == "Pilot study"
    assert found.status == ProjectStatus.PLANNING


def test_title_is_required(db: Session):
    with pytest.raises(IntegrityError):
        bad = Project(title=None, description="x")
        db.add(bad)
        db.flush()


def test_description_is_required(db: Session):
    with pytest.raises(IntegrityError):
        bad = Project(title="x", description=None)
        db.add(bad)
        db.flush()


def test_status_defaults_to_planning(db: Session, factories):
    proj = factories.project()
    db.flush()
    db.refresh(proj)
    assert proj.status == ProjectStatus.PLANNING


def test_status_accepts_each_valid_value(db: Session, factories):
    for status in ProjectStatus:
        factories.project(title=f"Project-{status.value}", status=status)
    db.flush()

    rows = db.exec(select(Project)).all()
    assert len(rows) == len(ProjectStatus)
