"""002_add_user_must_change_password

add must_change_password column to users table (BR-4: temp password flow).

Epic 1, task 1-7 (Quản lý người dùng — Admin).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_user_must_change_password"
down_revision: str = "001_create_projects"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
	op.add_column(
		"users",
		sa.Column(
			"must_change_password",
			sa.Boolean(),
			nullable=False,
			server_default=sa.text("false"),
		),
	)


def downgrade() -> None:
	op.drop_column("users", "must_change_password")
