"""Experiment ↔ Sample m:n join.

A sample may participate in many experiments; an experiment uses many samples
(spec lines 12 & 14). Composite PK ``(experiment_id, sample_id)`` enforces no
duplicates. ``assigned_at`` is symmetric with ``project_researchers.joined_at``
— a participation timestamp on the join row.

Both FKs are ``ON DELETE RESTRICT`` — labs archive, they don't delete; deleting
an experiment or sample that has assignments requires explicit handling first.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel


class ExperimentSample(SQLModel, table=True):
    __tablename__ = "experiment_samples"

    experiment_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("experiments.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    sample_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("samples.id", ondelete="RESTRICT"),
            primary_key=True,
            index=True,  # supports "experiments using this sample" queries
        ),
    )
    assigned_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
