"""Claims endpoints -- Task 4-4 FR-04 (api-spec §5).

RBAC: 🅞 owner-or-admin -- a Creator who doesn't own the project gets 403
(AC6), not 404 (which would leak whether the project exists to a stranger
less usefully than an explicit permission error, and matches the api-spec
🅞 legend's own wording).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.claim import VERDICTS
from app.models.project import Project
from app.models.user import User
from app.services.claim_service import ClaimNotFoundError, ClaimService

logger = logging.getLogger("avr.claims")

router = APIRouter(prefix="/projects/{project_id}", tags=["claims"])


class ClaimOut(BaseModel):
    id: str
    claim_text: str
    claim_type: str
    verdict: str
    evidence: list[dict]


class OverrideRequest(BaseModel):
    verdict: str
    reason: str


class OverrideResponse(BaseModel):
    claim: ClaimOut
    overall_verdict: str
    affected_claims: list[str]


async def _require_owner_or_admin(session, project_id: UUID, user: User) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not the project owner")
    return project


def _to_out(claim) -> ClaimOut:
    return ClaimOut(
        id=str(claim.id), claim_text=claim.claim_text, claim_type=claim.claim_type,
        verdict=claim.verdict, evidence=claim.evidence or [],
    )


@router.get("/claims", response_model=list[ClaimOut])
async def list_claims(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        await _require_owner_or_admin(db, project_id, user)
        svc = ClaimService(db)
        claims = await svc.list_for_project(project_id)
        return [_to_out(c) for c in claims]


@router.post("/claims/{claim_id}/override", response_model=OverrideResponse)
async def override_claim(
    request: Request,
    project_id: UUID,
    claim_id: UUID,
    body: OverrideRequest,
    user: User = Depends(get_current_user),
):
    if body.verdict not in VERDICTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"verdict must be one of {VERDICTS}"
        )

    async with request.app.state.database.session() as db:
        await _require_owner_or_admin(db, project_id, user)
        svc = ClaimService(db)
        try:
            claim = await svc.get(claim_id)
            if claim is None or claim.project_id != project_id:
                raise ClaimNotFoundError(f"claim {claim_id} not found")
            claim, overall, affected = await svc.override(
                claim, verdict=body.verdict, reason=body.reason, actor=str(user.id)
            )
        except ClaimNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        await db.commit()
        return OverrideResponse(
            claim=_to_out(claim), overall_verdict=overall, affected_claims=affected
        )
