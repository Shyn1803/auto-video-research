"""004_add_api_keys

Add api_keys table with Fernet-encrypted key storage (Task 3-4 FR-15).

Epic 3, task 3-4 (API Key Management).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "004_add_api_keys"
down_revision: str = "003_add_user_must_change_password"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("key_encrypted", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exhausted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'exhausted', 'revoked')",
            name="ck_api_keys_status",
        ),
    )
    op.create_index("ix_api_keys_provider", "api_keys", ["provider"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_status", table_name="api_keys")
    op.drop_index("ix_api_keys_provider", table_name="api_keys")
    op.drop_table("api_keys")
