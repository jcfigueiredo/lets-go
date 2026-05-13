"""Project aggregate root.

A unit of research work with title, description, and lifecycle status. The
``project_status`` enum drives the simple state machine planning → active →
{completed, cancelled}; the enforcement of transitions is a service-layer
concern, not a database one.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Column, DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class ProjectStatus(StrEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    title: str = Field(nullable=False)
    description: str = Field(nullable=False)
    # values_callable forces the wire format to use enum .value (lowercase) rather
    # than .name (uppercase). The Postgres enum type's values are .value-based, so
    # without this every INSERT raises "invalid input value for enum project_status".
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNING,
        sa_column=Column(
            SAEnum(
                ProjectStatus,
                name="project_status",
                values_callable=lambda enum: [e.value for e in enum],
            ),
            nullable=False,
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
