"""Seed entry point.

Hand-curated, deterministic data exercising the spec scenarios. Idempotent:
``make seed && make seed`` produces the same final state.

Idempotency strategy: ``INSERT … ON CONFLICT DO NOTHING`` on the natural
identifier (email, accession code, composite PK, etc.).
"""

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from lab.db import engine
from lab.models import Researcher, ResearcherRole


def _seed_researchers(session: Session) -> None:
    data = [
        {"name": "Alice Tan",   "email": "alice@lab.example",   "role": ResearcherRole.PRINCIPAL_INVESTIGATOR},
        {"name": "Bob Singh",   "email": "bob@lab.example",     "role": ResearcherRole.LAB_TECHNICIAN},
        {"name": "Carol Liu",   "email": "carol@lab.example",   "role": ResearcherRole.GRADUATE_STUDENT},
        {"name": "Diego Cruz",  "email": "diego@lab.example",   "role": ResearcherRole.POSTDOC},
    ]
    stmt = insert(Researcher).values(data).on_conflict_do_nothing(index_elements=["email"])
    session.execute(stmt)


def seed(session: Session) -> None:
    """Apply seed data idempotently."""
    _seed_researchers(session)


if __name__ == "__main__":  # pragma: no cover
    with Session(engine) as session:
        seed(session)
        session.commit()
