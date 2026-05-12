from sqlmodel import Session

from lab.seed import seed


def test_seed_runs_against_a_session_without_error(db: Session):
    seed(db)
    # No assertions on data — the schema design will add real seed scenarios.
    # Just proves the entry point is callable.
    assert db.is_active
