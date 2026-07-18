"""011_add_claims

Add claims table (Task 4-4, FR-03/04) per docs/specs/database-schema.md §2.4,
plus override-audit columns (BR-3: override never deletes evidence, just
records who/when/why -- see app/models/claim.py docstring).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "011_add_claims"
down_revision: str = "010_add_sources"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(20), nullable=False),
        sa.Column("verdict", sa.String(10), nullable=False, server_default="PENDING"),
        sa.Column(
            "evidence", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("overridden_by", sa.String(100), nullable=True),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "claim_type IN ('model_name','benchmark','release_date','paper','github','version','other')",
            name="ck_claims_claim_type",
        ),
        sa.CheckConstraint(
            "verdict IN ('PASS','WARN','FAIL','PENDING')", name="ck_claims_verdict"
        ),
    )
    op.create_index("idx_claims_project", "claims", ["project_id", "verdict"])


def downgrade() -> None:
    op.drop_index("idx_claims_project", table_name="claims")
    op.drop_table("claims")
