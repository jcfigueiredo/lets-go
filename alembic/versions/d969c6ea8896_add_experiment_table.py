"""add experiment table

Revision ID: d969c6ea8896
Revises: 922df8d00757
Create Date: 2026-05-13 13:16:06.691319

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d969c6ea8896"
down_revision: str | None = "922df8d00757"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("hypothesis", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "planned",
                "running",
                "completed",
                "cancelled",
                name="experiment_status",
            ),
            nullable=False,
        ),
        sa.Column("follows_up_experiment_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="experiment_date_order",
        ),
        sa.CheckConstraint(
            "follows_up_experiment_id IS NULL OR follows_up_experiment_id <> id",
            name="experiment_no_self_follow_up",
        ),
        sa.ForeignKeyConstraint(
            ["follows_up_experiment_id"], ["experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_experiments_follows_up_experiment_id", "experiments", ["follows_up_experiment_id"]
    )
    op.create_index("ix_experiments_project_id", "experiments", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_experiments_project_id", table_name="experiments")
    op.drop_index("ix_experiments_follows_up_experiment_id", table_name="experiments")
    op.drop_table("experiments")
    sa.Enum(name="experiment_status").drop(op.get_bind(), checkfirst=False)
