"""StepVersion model — versioned snapshots of each pipeline step."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project

# All pipeline steps in causal order — used for cascade-stale (BR-3).
# Restore on step N marks N+1, N+2, ... stale; N itself stays non-stale.
_STEP_ORDER: Sequence[str] = (
    "research",
    "outline",
    "script",
    "storyboard",
    "scene_set",
    "produce",
    "render",
    "publish",
)


class StepVersion(Base):
    """Immutable snapshot of a single pipeline step for a project.

    Per BR-1: never UPDATE ``content`` — always INSERT a new row.
    Per BR-4: "current" = max(version) WHERE NOT stale, or max(version) +
    all_stale=True when every version of that step is stale.
    """

    __tablename__ = "step_versions"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_by: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="step_versions",
    )

    __table_args__ = (
        CheckConstraint(
            "step IN ('research','outline','script','storyboard','scene_set',"
            "'produce','render','publish')",
            name="ck_step_versions_step",
        ),
        CheckConstraint("version >= 1", name="ck_step_versions_version_positive"),
    )
