"""004_api_keys 3-4 Add api_keys table (Fernet-encrypted key storage).

FR-15. Conforms to docs/specs/database-schema.md section 2.7.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# Dedicated revision so 001→003 chain is unambiguous.
revision: str = "004_add_api_keys"
# The migration after 003_add_status_history (the highest-numbered existing).
down_revision: str = "003_add_status_history_table"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("usage_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exhausted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','exhausted','revoked','invalid')",
            name="ck_api_keys_status",
        ),
    )
    op.create_index(
        "idx_api_keys_provider", "api_keys", ["provider", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_api_keys_provider", table_name="api_keys")
    op.drop_table("api_keys")
