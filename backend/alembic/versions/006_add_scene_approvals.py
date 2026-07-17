"""006_add_scene_approvals

Add scene_approvals table — per-scene approval flag, separate from the
versioned Scene render contract (Task 5-1, FR-09).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "006_add_scene_approvals"
down_revision: str = "005_add_llm_usage_partitioned"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scene_approvals",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("scene_id", sa.String(64), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
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
            "project_id", "scene_id", name="uq_scene_approvals_project_scene"
        ),
    )
    op.create_index("ix_scene_approvals_project_id", "scene_approvals", ["project_id"])
    op.create_index("ix_scene_approvals_scene_id", "scene_approvals", ["scene_id"])


def downgrade() -> None:
    op.drop_index("ix_scene_approvals_scene_id", table_name="scene_approvals")
    op.drop_index("ix_scene_approvals_project_id", table_name="scene_approvals")
    op.drop_table("scene_approvals")
