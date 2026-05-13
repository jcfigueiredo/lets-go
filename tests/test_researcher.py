import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from lab.models import Researcher, ResearcherRole


def test_create_and_read(db: Session, factories):
    alice = factories.researcher(name="Alice", email="alice@lab.example")
    db.flush()

    found = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    assert found.name == "Alice"
    assert found.role == ResearcherRole.LAB_TECHNICIAN


def test_email_is_unique(db: Session, factories):
    factories.researcher(email="dup@lab.example")
    db.flush()

    with pytest.raises(IntegrityError):
        factories.researcher(email="dup@lab.example")
        db.flush()


def test_name_is_required(db: Session):
    with pytest.raises(IntegrityError):
        bad = Researcher(name=None, email="x@lab.example", role=ResearcherRole.LAB_TECHNICIAN)
        db.add(bad)
        db.flush()


def test_role_accepts_each_valid_value(db: Session, factories):
    for role in ResearcherRole:
        factories.researcher(email=f"{role.value}@lab.example", role=role)
    db.flush()

    count = db.exec(select(Researcher)).all()
    assert len(count) == len(ResearcherRole)


def test_created_and_updated_at_have_server_defaults(db: Session, factories):
    r = factories.researcher()
    db.flush()
    db.refresh(r)

    assert r.created_at is not None
    assert r.updated_at is not None
