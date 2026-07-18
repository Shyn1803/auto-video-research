"""012_add_assets

Add assets table (Task 5-3, FR-20) per docs/specs/database-schema.md §2.5.
Every row must carry a non-empty license -- "unknown license" is rejected,
never stored (rules/security.md).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "012_add_assets"
down_revision: str = "011_add_claims"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=False),
        sa.Column(
            "attribution_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("attribution_text", sa.Text(), nullable=True),
        sa.Column(
            "media_type", sa.String(length=10), nullable=False, server_default="image"
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_assets_content_hash"),
        sa.CheckConstraint(
            "media_type IN ('image','video','audio')", name="ck_assets_media_type"
        ),
        sa.CheckConstraint("license <> ''", name="ck_assets_license_not_empty"),
    )
    op.create_index("ix_assets_provider", "assets", ["provider"])
    op.create_index("ix_assets_content_hash", "assets", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_assets_content_hash", table_name="assets")
    op.drop_index("ix_assets_provider", table_name="assets")
    op.drop_table("assets")
