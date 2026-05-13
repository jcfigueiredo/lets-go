"""Experiment aggregate root.

Belongs to exactly one project. May reference an earlier experiment as a follow-up
(replication, iteration, refined hypothesis). Status lifecycle is distinct from
project status (D7: separate enum, distinct value names).

CHECK constraints:
- ``experiment_date_order``: end_date must be on/after start_date when both present
- ``experiment_no_self_follow_up``: follows_up_experiment_id != id (single-row check;
  longer cycles A→B→A are NOT prevented at the DB level — domain-service concern)
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlmodel import Field, SQLModel


class ExperimentStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Experiment(SQLModel, table=True):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="experiment_date_order",
        ),
        CheckConstraint(
            "follows_up_experiment_id IS NULL OR follows_up_experiment_id <> id",
            name="experiment_no_self_follow_up",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    project_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    title: str = Field(nullable=False)
    hypothesis: str = Field(nullable=False)
    start_date: date | None = Field(default=None, nullable=True)
    end_date: date | None = Field(default=None, nullable=True)
    # values_callable forces wire format to use enum .value (lowercase). See
    # researcher.py for the longer rationale.
    status: ExperimentStatus = Field(
        default=ExperimentStatus.PLANNED,
        sa_column=Column(
            SAEnum(
                ExperimentStatus,
                name="experiment_status",
                values_callable=lambda enum: [e.value for e in enum],
            ),
            nullable=False,
        ),
    )
    follows_up_experiment_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("experiments.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )
