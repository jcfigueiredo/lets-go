"""add measurement table

Revision ID: f6bf29205893
Revises: 3278c7aa635e
Create Date: 2026-05-13 13:30:46.801587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6bf29205893'
down_revision: Union[str, None] = '3278c7aa635e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measurements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("sample_id", sa.BigInteger(), nullable=True),
        sa.Column("recorded_by", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "numeric",
                "categorical",
                "text",
                name="measurement_kind",
            ),
            nullable=False,
        ),
        sa.Column("numeric_value", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("categorical_value", sa.String(), nullable=True),
        sa.Column("text_value", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["researchers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_measurements_experiment_id", "measurements", ["experiment_id"])
    op.create_index("ix_measurements_kind", "measurements", ["kind"])
    op.create_index("ix_measurements_recorded_by", "measurements", ["recorded_by"])
    op.create_index("ix_measurements_sample_id", "measurements", ["sample_id"])


def downgrade() -> None:
    op.drop_index("ix_measurements_sample_id", table_name="measurements")
    op.drop_index("ix_measurements_recorded_by", table_name="measurements")
    op.drop_index("ix_measurements_kind", table_name="measurements")
    op.drop_index("ix_measurements_experiment_id", table_name="measurements")
    op.drop_table("measurements")
    sa.Enum(name="measurement_kind").drop(op.get_bind(), checkfirst=False)
