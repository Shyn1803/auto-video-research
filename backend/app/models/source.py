"""Source + SourceEmbedding models -- Task 4-3 FR-02 (docs/specs/database-schema.md §2.4).

``project_id`` NULL means a globally shared cache row (BR-3: don't
re-crawl a URL any project has already fetched within the cache TTL) --
per-project sources always have a non-NULL project_id.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    summary_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    partial_content: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    embedding: Mapped["SourceEmbedding | None"] = relationship(
        "SourceEmbedding", back_populates="source", cascade="all, delete-orphan", uselist=False
    )


class SourceEmbedding(Base):
    __tablename__ = "source_embeddings"

    source_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)

    source: Mapped[Source] = relationship("Source", back_populates="embedding")
