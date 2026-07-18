"""StepApproval model — per-step (outline/script/...) approval state.

Task 4-5 Step 8: `POST /projects/{id}/steps/{step}/approve` is declared in
api-spec.md §2 but had no implementation anywhere in the codebase until
this task built it (scoped here to `outline`/`script` — the two "sub-step
approve riêng" this task owns; other steps can reuse the same table/
service later without a new migration).

Kept separate from `StepVersion.content` on purpose — same reasoning as
`SceneApproval` (app/models/scene_approval.py): approval is UI/workflow
state (who approved which version, when), not render/generation content,
so it must never be smuggled into the versioned JSONB blob that
`VersioningService` treats as immutable+insert-only (BR-1).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StepApproval(Base):
    """Mutable per-(project, step) approval flag, always referring to a
    specific `version` at the time it was approved — an edit or
    regenerate after approval creates a *new* StepVersion row (BR-1), so
    the approval naturally goes stale (call site re-checks `version`
    against current before treating a step as "approved").
    """

    __tablename__ = "step_approvals"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "step", name="uq_step_approvals_project_step"),
    )
