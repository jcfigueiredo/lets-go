"""add project table and status enum

Revision ID: a6d6fbd3bbe9
Revises: 373b42ea399c
Create Date: 2026-05-13 12:20:18.197367

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6d6fbd3bbe9"
down_revision: str | None = "373b42ea399c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "planning",
                "active",
                "completed",
                "cancelled",
                name="project_status",
            ),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("projects")
    sa.Enum(name="project_status").drop(op.get_bind(), checkfirst=False)
