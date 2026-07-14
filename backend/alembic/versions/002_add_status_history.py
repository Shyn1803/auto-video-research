"""002_add_status_history 3 Add status_history table + index (FR-17).

Epic 1, task 1-4 (State machine).
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_status_history"
down_revision: str = "002_add_user_must_change_password"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "status_history",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_status_history_project",
        "status_history",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_status_history_project", table_name="status_history")
    op.drop_table("status_history")
