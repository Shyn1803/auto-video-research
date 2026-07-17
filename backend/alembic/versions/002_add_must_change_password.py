"""002_add_must_change_password_to_users

Add must_change_password to users for task 1-7 (BR-4: temp password flow).
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_must_change_password"
down_revision: str = "001_create_projects"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
