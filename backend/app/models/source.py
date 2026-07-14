"""Research source and embedding models (Task 4-3 FR-02 §2.4)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass


class Source(Base):
    """A crawled research source article.

    ``project_id`` is NULL for shared cache entries (BR-3: content_hash cache
    shared across projects).  The ``(project_id, url_hash)`` unique index
    deduplicates within a project; the partial index on ``url_hash`` where
    ``project_id IS NULL`` powers the shared-cache lookup.
    """

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    summary_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    partial_content: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    trusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    disabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "provider IN ('arxiv','hn','github','rss','searxng','manual','search')",
            name="ck_sources_provider",
        ),
        # Deduplication: same project + same url_hash → only one row
        Index("idx_sources_dedupe", "project_id", "url_hash", unique=True),
        # Shared cache lookup: project_id IS NULL (BR-3)
        Index(
            "idx_sources_shared_cache",
            "url_hash",
            postgresql_where=Text("project_id IS NULL"),
        ),
    )


class SourceEmbedding(Base):
    """Dense embedding for a source article (BGE-M3, 1024 dims).

    Primary key is also a FK so deleting a source cascades.
    """

    __tablename__ = "source_embeddings"

    source_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True
    )
    embedding_raw: Mapped[str] = mapped_column(Text, nullable=False)
