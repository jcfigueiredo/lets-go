"""replace single-column index on measurements.experiment_id with composite

Revision ID: 50e553999104
Revises: f6bf29205893
Create Date: 2026-05-13 14:41:35.952120

"""

from collections.abc import Sequence

from alembic import op

revision: str = "50e553999104"
down_revision: str | None = "f6bf29205893"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_measurements_experiment_id", table_name="measurements")
    op.create_index(
        "ix_measurements_experiment_id_recorded_at",
        "measurements",
        ["experiment_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_measurements_experiment_id_recorded_at", table_name="measurements")
    op.create_index("ix_measurements_experiment_id", "measurements", ["experiment_id"])
