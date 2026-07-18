"""012_add_step_approvals

Add step_approvals table — per-(project, step) approval flag, always
pinned to the version it was approved at (Task 4-5 Step 8).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "012_add_step_approvals"
down_revision: str = "011_add_claims"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "step_approvals",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("step", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "project_id", "step", name="uq_step_approvals_project_step"
        ),
    )
    op.create_index("ix_step_approvals_project_id", "step_approvals", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_step_approvals_project_id", table_name="step_approvals")
    op.drop_table("step_approvals")
