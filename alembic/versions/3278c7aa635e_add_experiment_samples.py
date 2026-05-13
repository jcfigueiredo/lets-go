"""add experiment_samples

Revision ID: 3278c7aa635e
Revises: d969c6ea8896
Create Date: 2026-05-13 13:23:13.476608

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3278c7aa635e"
down_revision: str | None = "d969c6ea8896"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_samples",
        sa.Column("experiment_id", sa.BigInteger(), nullable=False),
        sa.Column("sample_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("experiment_id", "sample_id"),
    )
    # Composite PK only indexes leading-column lookups; add a secondary index on
    # sample_id to support "which experiments use sample X?" queries.
    op.create_index(
        "ix_experiment_samples_sample_id",
        "experiment_samples",
        ["sample_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_experiment_samples_sample_id", table_name="experiment_samples")
    op.drop_table("experiment_samples")
