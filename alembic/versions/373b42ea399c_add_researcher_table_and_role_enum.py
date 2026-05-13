"""add researcher table and role enum

Revision ID: 373b42ea399c
Revises:
Create Date: 2026-05-13 10:10:48.322545

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "373b42ea399c"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "researchers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "principal_investigator",
                "lab_technician",
                "graduate_student",
                "postdoc",
                "undergraduate",
                name="researcher_role",
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
        sa.UniqueConstraint("email", name="uq_researchers_email"),
    )


def downgrade() -> None:
    op.drop_table("researchers")
    sa.Enum(name="researcher_role").drop(op.get_bind(), checkfirst=False)
