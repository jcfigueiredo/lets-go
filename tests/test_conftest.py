from sqlalchemy import text
from sqlmodel import Session


def test_db_fixture_yields_open_session(db: Session):
    assert db.is_active

    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_db_fixture_allows_inner_commit_within_savepoint(db: Session):
    """An inner commit should not raise; the savepoint restarts under the hood."""
    db.execute(text("CREATE TEMP TABLE _marker (x INT) ON COMMIT DROP"))
    db.execute(text("INSERT INTO _marker VALUES (1)"))
    db.commit()  # commits the SAVEPOINT; outer transaction still open

    # After the inner commit, the session must still be usable because the
    # listener re-opened a fresh SAVEPOINT. If the outer transaction had
    # been committed (ON COMMIT DROP), the temp table would be gone; if the
    # session had been closed, the next execute would raise. Both invariants
    # are checked at once.
    assert db.is_active
    rows = db.execute(text("SELECT count(*) FROM _marker")).scalar()
    assert rows == 1


def test_db_fixture_rolls_back_test_isolation_first(db: Session):
    """Part 1 of an isolation pair: insert a marker into a real table."""
    db.execute(text("INSERT INTO alembic_version (version_num) VALUES ('isolation_marker')"))
    db.commit()

    count = db.execute(
        text("SELECT count(*) FROM alembic_version WHERE version_num = 'isolation_marker'")
    ).scalar()
    assert count == 1


def test_db_fixture_rolls_back_test_isolation_second(db: Session):
    """Part 2: previous test's marker must not be visible — proof of rollback."""
    count = db.execute(
        text("SELECT count(*) FROM alembic_version WHERE version_num = 'isolation_marker'")
    ).scalar()
    assert count == 0
