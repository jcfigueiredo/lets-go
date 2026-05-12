from sqlalchemy import text
from sqlmodel import Session


def test_db_fixture_wiring_produces_an_active_session(db: Session):
    """Smoke test: the fixture's setup chain (engine → connection → outer
    transaction → SAVEPOINT → Session binding) succeeded, yielding a session
    that is active and can execute SQL."""
    assert db.is_active

    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_db_fixture_commit_inside_test_does_not_end_session(db: Session):
    """`session.commit()` inside a test must NOT end the test's outer transaction.

    The SAVEPOINT pattern's ``after_transaction_end`` listener restarts a fresh
    SAVEPOINT each time the previous one ends, so the session remains usable
    for the rest of the test. Without this behavior, any test that calls
    ``commit()`` mid-body (e.g., to test constraint behavior at commit time)
    would be unable to run further assertions.
    """
    db.execute(text("CREATE TEMP TABLE _marker (x INT) ON COMMIT DROP"))
    db.execute(text("INSERT INTO _marker VALUES (1)"))
    db.commit()

    assert db.is_active
    rows = db.execute(text("SELECT count(*) FROM _marker")).scalar()
    assert rows == 1
