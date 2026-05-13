"""add project_researchers

Revision ID: 98559e20c786
Revises: a6d6fbd3bbe9
Create Date: 2026-05-13 12:30:49.482340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '98559e20c786'
down_revision: Union[str, None] = 'a6d6fbd3bbe9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_researchers",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("researcher_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["researcher_id"], ["researchers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("project_id", "researcher_id"),
    )
    # Composite PK only indexes leading-column lookups; add a secondary index on
    # researcher_id to support "which projects is researcher X on?" queries.
    op.create_index(
        "ix_project_researchers_researcher_id",
        "project_researchers",
        ["researcher_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_researchers_researcher_id", table_name="project_researchers")
    op.drop_table("project_researchers")
