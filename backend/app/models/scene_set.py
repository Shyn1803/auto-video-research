"""Scene Set model — owns semantic_tree, resolved JSON, layout_override, motion_plan.

Step 10 of 4-6: persisted container for the Layout Engine pipeline output.
A scene_set version stores one complete resolution pass; multiple versions
track regeneration history.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class SceneSet(Base):
    """Top-level scene set — owns a project's layout resolution history."""

    __tablename__ = "scene_sets"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.now(timezone.utc)
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    semantic_tree_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    layout_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── relationships ──────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="scene_sets")
    versions: Mapped[list["SceneSetVersion"]] = relationship(
        back_populates="scene_set", cascade="all, delete-orphan", order_by="SceneSetVersion.version"
    )


class SceneSetVersion(Base):
    """A single resolution pass (semantic_tree → classifier → resolve → motion_plan)."""

    __tablename__ = "scene_set_versions"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    scene_set_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("scene_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ── Layout Engine outputs ──────────────────────────────────────────────
    semantic_tree: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resolved_scene: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    layout_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    layout_override_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    layout_override_release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    motion_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    resolution_failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Promoted aggregates (denormalised for query performance)
    total_scenes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_duration_s: Mapped[float | None] = mapped_column(Text, nullable=True)  # stored as string for precision
    class_distribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── relationships ──────────────────────────────────────────────────────
    scene_set: Mapped["SceneSet"] = relationship(back_populates="versions")

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_version_positive"),
        CheckConstraint("total_scenes IS NULL OR total_scenes >= 0", name="ck_total_scenes_nonneg"),
    )
