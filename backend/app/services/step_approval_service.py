"""StepApprovalService -- Task 4-5 Step 8.

First real implementation of `POST /projects/{id}/steps/{step}/approve`
(declared in api-spec.md §2, never built before this task). Scoped here
to `outline`/`script` (this task's "2 sub-step approve riêng" requirement)
-- other steps can reuse this same service/table without a migration, but
wiring them into the broader run/approve pipeline control flow (state
machine transitions per step) is out of this task's scope; flagged as a
follow-up rather than solved here (same "don't solve the systemic problem
inside one task" posture as the node-wiring tension in
patterns/langgraph-pipeline-node.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step_approval import StepApproval
from app.services.versioning_service import VersioningService

APPROVABLE_STEPS = ("outline", "script")


class StepApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._versions = VersioningService(db)

    async def approve(
        self, *, project_id: UUID, step: str, actor: str
    ) -> StepApproval:
        if step not in APPROVABLE_STEPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"step {step!r} is not approvable (only {APPROVABLE_STEPS})",
            )

        current, all_stale = await self._versions.current(project_id, step)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no version for step {step!r} to approve",
            )
        if all_stale:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"current version of step {step!r} is stale -- regenerate first",
            )

        result = await self._db.execute(
            select(StepApproval).where(
                StepApproval.project_id == project_id, StepApproval.step == step
            )
        )
        approval = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if approval is None:
            approval = StepApproval(
                project_id=project_id,
                step=step,
                version=current.version,
                approved=True,
                approved_at=now,
                approved_by=actor,
            )
            self._db.add(approval)
        else:
            approval.version = current.version
            approval.approved = True
            approval.approved_at = now
            approval.approved_by = actor

        await self._db.flush()
        return approval

    async def is_current_approved(self, project_id: UUID, step: str) -> bool:
        """True only if an approval exists AND it's pinned to the version
        that's actually current right now (an edit/regenerate after
        approval creates a new StepVersion row, per BR-1, which makes any
        prior approval stale without needing a cascade write)."""
        current, all_stale = await self._versions.current(project_id, step)
        if current is None or all_stale:
            return False
        result = await self._db.execute(
            select(StepApproval).where(
                StepApproval.project_id == project_id, StepApproval.step == step
            )
        )
        approval = result.scalar_one_or_none()
        if approval is None or not approval.approved:
            return False
        return approval.version == current.version
