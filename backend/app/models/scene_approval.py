"""SceneApproval model — per-scene approval state (Task 5-1, FR-09).

Kept separate from the Scene render contract (``app/schemas/scene.py``) on
purpose: ``Scene`` is ``extra="forbid"`` and is the Remotion render/cache-key
contract, so UI-only workflow state (who approved a scene, when) must never
be smuggled into that JSON — see rules/architecture.md "Layout Engine
boundary" and rules/type-safety.md. Approval is keyed by ``scene_id``, which
is stable across ``step_versions`` (scene_set) rows, so it survives autosave
creating a new version.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SceneApproval(Base):
    """Mutable per-scene approval flag, one row per (project_id, scene_id)."""

    __tablename__ = "scene_approvals"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    scene_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "scene_id", name="uq_scene_approvals_project_scene"),
    )
