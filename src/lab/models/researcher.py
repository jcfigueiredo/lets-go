"""Researcher aggregate root.

A scientist who runs experiments. Has identity, contact, and a lab-global role.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, Enum as SAEnum, func
from sqlmodel import Field, SQLModel


class ResearcherRole(StrEnum):
    PRINCIPAL_INVESTIGATOR = "principal_investigator"
    LAB_TECHNICIAN = "lab_technician"
    GRADUATE_STUDENT = "graduate_student"
    POSTDOC = "postdoc"
    UNDERGRADUATE = "undergraduate"


class Researcher(SQLModel, table=True):
    __tablename__ = "researchers"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True)
    role: ResearcherRole = Field(
        sa_column=Column(
            SAEnum(
                ResearcherRole,
                name="researcher_role",
                values_callable=lambda enum: [e.value for e in enum],
            ),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        sa_column_kwargs={"server_default": func.now()},
        nullable=False,
    )
    updated_at: datetime = Field(
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
        nullable=False,
    )
