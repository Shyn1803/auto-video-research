"""010_add_sources

Add sources / source_embeddings tables (Task 4-3, FR-02) per
docs/specs/database-schema.md §2.4. Requires the pgvector extension for
the embedding column + HNSW index (BGE-M3, 1024-dim).
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "010_add_sources"
down_revision: str = "009_add_prompts"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sources",
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
            nullable=True,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("summary_vi", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("partial_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("trusted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sources_url_hash", "sources", ["url_hash"])
    op.create_index("idx_sources_content_hash", "sources", ["content_hash"])
    op.create_index(
        "idx_sources_dedupe", "sources", ["project_id", "url_hash"], unique=True
    )
    op.create_index(
        "idx_sources_shared_cache",
        "sources",
        ["url_hash"],
        unique=False,
        postgresql_where=sa.text("project_id IS NULL"),
    )

    op.execute(
        """
        CREATE TABLE source_embeddings (
            source_id UUID PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
            embedding vector(1024) NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_source_embeddings_hnsw ON source_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source_embeddings")
    op.drop_index("idx_sources_shared_cache", table_name="sources")
    op.drop_index("idx_sources_dedupe", table_name="sources")
    op.drop_index("idx_sources_content_hash", table_name="sources")
    op.drop_index("idx_sources_url_hash", table_name="sources")
    op.drop_table("sources")
