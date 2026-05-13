"""Project ↔ Researcher membership.

Composite PK (project_id, researcher_id). The ``joined_at`` timestamp records
when the researcher started on the project (D2 in the schema design). Both FKs
are ``ON DELETE RESTRICT`` — labs archive, they don't delete.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel


class ProjectResearcher(SQLModel, table=True):
    __tablename__ = "project_researchers"

    project_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("projects.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    researcher_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("researchers.id", ondelete="RESTRICT"),
            primary_key=True,
            index=True,
        ),
    )
    joined_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
