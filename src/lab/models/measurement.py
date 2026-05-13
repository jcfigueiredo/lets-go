"""Measurement aggregate root (per D1 + D3 in the schema design).

Polymorphic via Single Table Inheritance: one ``measurements`` table holds all
kinds, with a ``kind`` discriminator and a CHECK constraint enforcing the
contract:

  kind = 'numeric'     → numeric_value + unit populated; others NULL
  kind = 'categorical' → categorical_value populated; others NULL
  kind = 'text'        → text_value populated; others NULL

Adding a new kind requires a migration (ALTER TYPE + ALTER TABLE for the CHECK
constraint) — the spec says new kinds appear "occasionally," not constantly,
so this cadence is acceptable. If reality is closer to "new kind every sprint,"
revisit toward JSONB.

The aggregate is independent (D1): ``experiment_id`` and ``sample_id`` FKs both
use ``ON DELETE RESTRICT``. Cross-table invariants ("measurement timestamp ∈
experiment date range", "no measurements after experiment is completed") are
domain-service rules — Postgres CHECK can't span tables.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    func,
)
from sqlmodel import Field, SQLModel


class MeasurementKind(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"


class Measurement(SQLModel, table=True):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(
            """(
                (kind = 'numeric'     AND numeric_value IS NOT NULL AND unit IS NOT NULL
                                      AND categorical_value IS NULL AND text_value IS NULL)
             OR (kind = 'categorical' AND categorical_value IS NOT NULL
                                      AND numeric_value IS NULL AND unit IS NULL AND text_value IS NULL)
             OR (kind = 'text'        AND text_value IS NOT NULL
                                      AND numeric_value IS NULL AND unit IS NULL AND categorical_value IS NULL)
            )""",
            name="measurement_value_matches_kind",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    experiment_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("experiments.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    sample_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("samples.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    recorded_by: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("researchers.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    recorded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    # values_callable forces wire format to use enum .value (lowercase). See
    # researcher.py for the full rationale.
    kind: MeasurementKind = Field(
        sa_column=Column(
            SAEnum(
                MeasurementKind,
                name="measurement_kind",
                values_callable=lambda enum: [e.value for e in enum],
            ),
            nullable=False,
            index=True,
        ),
    )
    numeric_value: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric, nullable=True),
    )
    unit: str | None = Field(default=None, nullable=True)
    categorical_value: str | None = Field(default=None, nullable=True)
    text_value: str | None = Field(default=None, nullable=True)
    notes: str | None = Field(default=None, nullable=True)
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
