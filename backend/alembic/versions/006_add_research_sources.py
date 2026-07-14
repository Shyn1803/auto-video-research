"""006_add_research_sources

Create sources and source_embeddings tables for Task 4-3 FR-02 research phase.

Per docs/specs/database-schema.md §2.4:
- sources: crawled articles with url_hash dedupe and content_hash cache key
- source_embeddings: BGE-M3 1024-d vectors for similarity dedupe (BR-2)

Enables pgvector extension and creates HNSW index on embedding column.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "006_add_research_sources"
down_revision: str = "005_add_llm_usage_partitioned"
depends_on: list[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID,
            url TEXT NOT NULL,
            url_hash VARCHAR(64) NOT NULL,
            title TEXT,
            author TEXT,
            published_at TIMESTAMPTZ,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            summary_vi TEXT,
            content TEXT,
            content_hash VARCHAR(64),
            provider VARCHAR(30) NOT NULL,
            partial_content BOOLEAN NOT NULL DEFAULT false,
            trusted BOOLEAN NOT NULL DEFAULT false,
            pinned BOOLEAN NOT NULL DEFAULT false,
            disabled BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_sources_provider
                CHECK (provider IN ('arxiv','hn','github','rss','searxng','manual','search'))
        )
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX idx_sources_dedupe ON sources(project_id, url_hash)"
    )
    op.execute(
        sa.text(
            "CREATE INDEX idx_sources_shared_cache "
            "ON sources(url_hash) WHERE project_id IS NULL"
        )
    )
    op.execute(
        "CREATE INDEX idx_sources_project ON sources(project_id) "
        "WHERE project_id IS NOT NULL AND disabled = false"
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
        "CREATE INDEX idx_source_embeddings_hnsw "
        "ON source_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_source_embeddings_hnsw", table_name="source_embeddings")
    op.drop_table("source_embeddings")
    op.drop_index("idx_sources_project", table_name="sources")
    op.drop_index("idx_sources_shared_cache", table_name="sources")
    op.drop_index("idx_sources_dedupe", table_name="sources")
    op.drop_table("sources")
