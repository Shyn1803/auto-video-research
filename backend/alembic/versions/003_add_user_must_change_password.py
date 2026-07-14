"""003_add_user_must_change_password 3 Add must_change_password to users (BR-4).

Epic 1, task 1-7 (Quản lý người dùng — Admin).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "003_add_user_must_change_password"
down_revision: str = "002_add_status_history"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index("idx_users_must_change_password", "users", ["must_change_password"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_users_must_change_password", table_name="users")
    op.drop_column("users", "must_change_password")
