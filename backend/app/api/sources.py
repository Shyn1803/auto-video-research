"""Sources endpoints -- PATCH pinned/disabled (api-spec §4), with the BR-5
factcheck cascade recompute on disable (Task 4-4 Step 7).

Only the fields this task's scope actually needs (disable -> cascade) are
implemented here; list/create/delete (api-spec §4's other rows) belong to
whichever task owns the Sources UI (5-6) wiring the rest of that CRUD.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.project import Project
from app.models.source import Source
from app.models.user import User
from app.services.claim_service import ClaimService

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources"])


class SourcePatchRequest(BaseModel):
    pinned: bool | None = None
    disabled: bool | None = None


class SourcePatchResponse(BaseModel):
    source_id: str
    disabled: bool
    overall_verdict: str | None = None
    affected_claims: list[str] = []


async def _require_owner_or_admin(session, project_id: UUID, user: User) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not the project owner")
    return project


@router.patch("/{source_id}", response_model=SourcePatchResponse)
async def patch_source(
    request: Request,
    project_id: UUID,
    source_id: UUID,
    body: SourcePatchRequest,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        await _require_owner_or_admin(db, project_id, user)

        source = await db.get(Source, source_id)
        if source is None or source.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "source not found")

        was_disabled = source.disabled
        if body.pinned is not None:
            source.pinned = body.pinned
        if body.disabled is not None:
            source.disabled = body.disabled
        db.add(source)
        await db.flush()

        overall_verdict = None
        affected: list[str] = []
        newly_disabled = body.disabled is True and not was_disabled
        if newly_disabled:
            # BR-5: cascade recompute synchronously, same response.
            claim_svc = ClaimService(db)
            overall_verdict, affected = await claim_svc.recompute_after_source_change(
                project_id, str(source_id)
            )

        await db.commit()
        return SourcePatchResponse(
            source_id=str(source.id),
            disabled=source.disabled,
            overall_verdict=overall_verdict,
            affected_claims=affected,
        )
