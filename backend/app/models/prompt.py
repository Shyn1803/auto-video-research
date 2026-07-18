"""Prompt + PromptVersion models -- Task 4-2 FR-14.

``prompts`` is the stable identity (name = "research.summarize" etc, tier).
``prompt_versions`` is an append-only history per prompt: activating a
version flips its ``is_active`` on and every sibling version's off in the
same transaction. BR-1 (exactly one active version per prompt) is enforced
at the DB layer via a partial unique index, not application locking alone
-- see migration 009_add_prompts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prompt(Base):
    """Stable prompt identity -- name never changes once created."""

    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    versions: Mapped[list[PromptVersion]] = relationship(
        "PromptVersion", back_populates="prompt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "tier IN ('cheap','strong','embedding')", name="ck_prompts_tier"
        ),
    )


class PromptVersion(Base):
    """Immutable per-version snapshot. Rollback = activate an older row,
    never a copy (BR-5) -- history stays straight-line."""

    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    prompt_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    evaluated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    activated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="versions")

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_prompt_versions_version_positive"),
    )
