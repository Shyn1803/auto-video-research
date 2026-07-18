"""009_add_prompts

Add prompts / prompt_versions tables (Task 4-2, FR-14). BR-1 (exactly one
active version per prompt) is enforced by a partial unique index on
(prompt_id) WHERE is_active -- a second concurrent activate cannot both
succeed even under a race (AC5).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "009_add_prompts"
down_revision: str = "008_add_pipeline_runs"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_prompts_name"),
        sa.CheckConstraint(
            "tier IN ('cheap','strong','embedding')", name="ck_prompts_tier"
        ),
    )
    op.create_index("ix_prompts_name", "prompts", ["name"])

    op.create_table(
        "prompt_versions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("variables", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evaluated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("activated_by", sa.String(100), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("version >= 1", name="ck_prompt_versions_version_positive"),
    )
    op.create_index(
        "ix_prompt_versions_prompt_id", "prompt_versions", ["prompt_id"]
    )
    # BR-1: exactly one active version per prompt, enforced by the DB even
    # under a concurrent-activate race (AC5) -- not application locking alone.
    op.create_index(
        "uq_prompt_versions_one_active_per_prompt",
        "prompt_versions",
        ["prompt_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_prompt_versions_one_active_per_prompt", table_name="prompt_versions"
    )
    op.drop_index("ix_prompt_versions_prompt_id", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_prompts_name", table_name="prompts")
    op.drop_table("prompts")
