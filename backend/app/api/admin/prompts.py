"""Admin › Prompts endpoints (Task 4-2 FR-14).

GET    /api/admin/prompts                         list all prompts
GET    /api/admin/prompts/{name}/versions          version history (BR-5 straight-line)
POST   /api/admin/prompts/{name}/versions          save new version (BR-3 -> 400)
POST   /api/admin/prompts/{name}/versions/{v}/activate   activate/rollback (BR-1, BR-2, BR-5)

RBAC: admin-only (require_role("admin")) on every route -- Creator gets 403 (AC3).
Contract change: none (net-new resource).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User
from app.services.prompt_service import (
    ActivateConflictError,
    PromptNotFoundError,
    PromptService,
    PromptValidationError,
)

logger = logging.getLogger("avr.admin.prompts")

router = APIRouter(prefix="/api/admin/prompts", tags=["admin: prompts"])


class PromptOut(BaseModel):
    name: str
    tier: str
    description: str | None


class PromptVersionOut(BaseModel):
    version: int
    template: str
    variables: list[str]
    is_active: bool
    evaluated: bool
    created_by: str
    activated_by: str | None


class CreateVersionRequest(BaseModel):
    template: str
    variables: list[str]


class ActivateResponse(BaseModel):
    version: int
    is_active: bool
    warning: bool  # BR-2: true when this version hasn't run eval yet


def _to_out(v) -> PromptVersionOut:
    return PromptVersionOut(
        version=v.version,
        template=v.template,
        variables=v.variables,
        is_active=v.is_active,
        evaluated=v.evaluated,
        created_by=v.created_by,
        activated_by=v.activated_by,
    )


@router.get("", response_model=list[PromptOut])
async def list_prompts(
    request: Request,
    user: User = Depends(require_role("admin")),
):
    async with request.app.state.database.session() as db:
        from sqlalchemy import select

        from app.models.prompt import Prompt

        rows = (await db.execute(select(Prompt))).scalars().all()
        return [PromptOut(name=p.name, tier=p.tier, description=p.description) for p in rows]


@router.get("/{name}/versions", response_model=list[PromptVersionOut])
async def list_versions(
    request: Request,
    name: str,
    user: User = Depends(require_role("admin")),
):
    async with request.app.state.database.session() as db:
        svc = PromptService(db)
        try:
            versions = await svc.list_versions(name)
        except PromptNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        return [_to_out(v) for v in versions]


@router.post(
    "/{name}/versions", response_model=PromptVersionOut, status_code=status.HTTP_201_CREATED
)
async def create_version(
    request: Request,
    name: str,
    body: CreateVersionRequest,
    user: User = Depends(require_role("admin")),
):
    async with request.app.state.database.session() as db:
        svc = PromptService(db)
        try:
            version = await svc.create_version(
                name, body.template, body.variables, actor=str(user.id)
            )
        except PromptValidationError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        except PromptNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        await db.commit()
        return _to_out(version)


@router.post("/{name}/versions/{version}/activate", response_model=ActivateResponse)
async def activate_version(
    request: Request,
    name: str,
    version: int,
    user: User = Depends(require_role("admin")),
):
    """Activate (or rollback to) *version* -- same operation either way (BR-5)."""
    async with request.app.state.database.session() as db:
        svc = PromptService(db)
        try:
            activated, warning = await svc.activate(name, version, actor=str(user.id))
        except PromptNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        except ActivateConflictError as exc:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        await db.commit()
        logger.info(
            "prompt activate: name=%s version=%s actor=%s warning=%s",
            name, version, user.id, warning,
        )
        return ActivateResponse(version=activated.version, is_active=True, warning=warning)
