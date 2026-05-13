from sqlmodel import Session, select, func

from lab.models import Researcher
from lab.seed import seed


def test_seed_runs_against_a_session_without_error(db: Session):
    seed(db)
    assert db.is_active


def test_seed_creates_researchers(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Researcher)).one()
    assert count == 4


def test_seed_is_idempotent(db: Session):
    seed(db)
    db.flush()
    first = db.exec(select(func.count()).select_from(Researcher)).one()

    seed(db)
    db.flush()
    second = db.exec(select(func.count()).select_from(Researcher)).one()

    assert first == second == 4
