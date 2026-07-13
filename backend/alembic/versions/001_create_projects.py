"""001_create_projects

projects + status_history tables for Epic 1 story 1-3 (FR-01).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "001_create_projects"
down_revision: str | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=20), server_default="interactive", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("language", sa.String(length=10), server_default="vi", nullable=False),
        sa.Column(
            "formats",
            sa.ARRAY(sa.Text()),
            server_default="{vertical_1080x1920}",
            nullable=False,
        ),
        sa.Column("voice_id", sa.Text(), nullable=True),
        sa.Column("voice_gender", sa.String(length=10), nullable=True),
        sa.Column("cloned_from", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "mode IN ('interactive','daily_news')", name="ck_projects_mode"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','RESEARCHING','NEED_REVIEW','REVISING',"
            " 'APPROVED','PRODUCING','RENDERING','READY',"
            " 'PUBLISHING','PUBLISHED','FAILED','ARCHIVED')",
            name="ck_projects_status",
        ),
        sa.CheckConstraint(
            "voice_gender IS NULL OR voice_gender IN ('female','male')",
            name="ck_projects_voice_gender",
        ),
    )
    op.create_index("idx_projects_owner_status", "projects", ["owner_id", "status"], unique=False)
    op.create_index("idx_projects_updated", "projects", ["updated_at"], unique=False, postgresql_using="btree", postgresql_ops={"updated_at": "DESC"})

    op.create_table(
        "step_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("step", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_version", sa.Integer(), nullable=True),
        sa.Column("content", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "step IN ('research','outline','script','storyboard','scene_set')",
            name="ck_step_versions_step",
        ),
    )
    op.create_index(
        "idx_step_versions_lookup",
        "step_versions",
        ["project_id", "step", sa.text("version DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_step_versions_lookup", table_name="step_versions")
    op.drop_table("step_versions")
    op.drop_index("idx_projects_updated", table_name="projects")
    op.drop_index("idx_projects_owner_status", table_name="projects")
    op.drop_table("projects")
