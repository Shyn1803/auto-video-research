"""006_add_pipeline_runs

Add pipeline_runs table -- Task 4-1 (LangGraph skeleton + checkpoint +
human gate). Lightweight index row per run; the full LangGraph checkpoint
(graph position, PipelineState) lives in the langgraph-checkpoint-postgres
library's own tables, created at app startup via app/pipeline/checkpoint.py
(langgraph owns that schema, not alembic -- see Task 4-1 Step 2 note).

Epic 4, task 4-1.
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "006_add_pipeline_runs"
down_revision: str = "005_add_llm_usage_partitioned"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_node", sa.String(20), nullable=True),
        sa.Column("interrupted_node", sa.String(20), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("previous_status", sa.String(20), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending','running','interrupted','approved',"
            "'completed','failed','cancelled')",
            name="ck_pipeline_runs_status",
        ),
    )
    op.create_index("ix_pipeline_runs_project_id", "pipeline_runs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_project_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
