"""Seed entry point.

Currently a no-op stub. Real seed scenarios land with the schema design;
see docs/superpowers/specs/2026-05-12-core-infra-design.md for the four
spec-required scenarios that will be exercised here.
"""

from sqlmodel import Session

from lab.db import engine


def seed(session: Session) -> None:
    """Apply seed data to the given session. No-op until schema lands."""
    return


if __name__ == "__main__":  # pragma: no cover
    with Session(engine) as session:
        seed(session)
        session.commit()
