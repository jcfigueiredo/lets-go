"""add sample table

Revision ID: 922df8d00757
Revises: 98559e20c786
Create Date: 2026-05-13 13:06:08.944813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '922df8d00757'
down_revision: Union[str, None] = '98559e20c786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "samples",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("accession_code", sa.String(), nullable=False),
        sa.Column("specimen_type", sa.String(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("storage_location", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_code", name="uq_samples_accession_code"),
    )


def downgrade() -> None:
    op.drop_table("samples")
