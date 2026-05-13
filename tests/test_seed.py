from sqlmodel import Session, select, func

from lab.models import Project, Researcher
from lab.seed import seed


def test_seed_runs_against_a_session_without_error(db: Session):
    seed(db)
    assert db.is_active


def test_seed_creates_researchers(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Researcher)).one()
    assert count == 4


def test_seed_creates_projects(db: Session):
    seed(db)
    db.flush()

    count = db.exec(select(func.count()).select_from(Project)).one()
    assert count == 2


def test_seed_is_idempotent(db: Session):
    """Idempotency: re-running seed must not change row counts AND must not overwrite existing rows."""
    seed(db)
    db.flush()
    r1 = db.exec(select(func.count()).select_from(Researcher)).one()
    p1 = db.exec(select(func.count()).select_from(Project)).one()

    # Mutate a row; if seed accidentally upserts, this change will be reverted.
    alice = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()
    alice.name = "Alice Tan (renamed)"
    db.flush()

    seed(db)
    db.flush()
    r2 = db.exec(select(func.count()).select_from(Researcher)).one()
    p2 = db.exec(select(func.count()).select_from(Project)).one()
    alice_after = db.exec(select(Researcher).where(Researcher.email == "alice@lab.example")).one()

    assert (r1, p1) == (r2, p2) == (4, 2)
    assert alice_after.name == "Alice Tan (renamed)", "Seed must not overwrite existing rows"
