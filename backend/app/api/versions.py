"""Version history endpoints (task 1-5, api-spec §3).

Follows the same request-scoped session pattern as app/api/projects.py and
app/api/users.py (``async with request.app.state.database.session() as db``)
— there is no FastAPI ``Depends``-based session getter in this codebase.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.deps import get_current_user
from app.models.project import Project
from app.models.step_version import StepVersion
from app.models.user import User
from app.schemas.version import (
    CompareResponse,
    CurrentResponse,
    RestoreResponse,
    VersionCreate,
    VersionListResponse,
    VersionOut,
)
from app.services.state_machine import ProjectStatus
from app.services.versioning_service import VersioningService

router = APIRouter(tags=["versions"])

# BR: restore is rejected with 409 while the project is actively running a step.
_RUNNING_STATUSES = {
    ProjectStatus.RESEARCHING,
    ProjectStatus.PRODUCING,
    ProjectStatus.RENDERING,
    ProjectStatus.PUBLISHING,
}


def _out(v: StepVersion) -> VersionOut:
    return VersionOut(
        id=str(v.id),
        version=v.version,
        step=v.step,
        stale=v.stale,
        parent_version=v.parent_version,
        created_by=v.created_by,
        created_at=v.created_at.isoformat(),
    )


@router.get(
    "/projects/{project_id}/steps/{step}/versions",
    response_model=VersionListResponse,
)
async def list_versions(
    request: Request,
    project_id: str,
    step: str,
    user: User = Depends(get_current_user),
) -> VersionListResponse:
    async with request.app.state.database.session() as db:
        proj = await _get_project(db, project_id, user.id)
        res = await db.execute(
            select(StepVersion)
            .where(StepVersion.project_id == proj.id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
        )
        return VersionListResponse(versions=[_out(v) for v in res.scalars().all()])


@router.get(
    "/projects/{project_id}/steps/{step}/current",
    response_model=CurrentResponse,
)
async def current_version(
    request: Request,
    project_id: str,
    step: str,
    user: User = Depends(get_current_user),
) -> CurrentResponse:
    """BR-4: current = max(version) WHERE NOT stale, or max(version) + all_stale."""
    async with request.app.state.database.session() as db:
        proj = await _get_project(db, project_id, user.id)
        svc = VersioningService(db)
        version, all_stale = await svc.current(proj.id, step)
        if version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no version for this step")
        return CurrentResponse(current=_out(version), all_stale=all_stale)


@router.post(
    "/projects/{project_id}/steps/{step}/versions",
    response_model=VersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    request: Request,
    project_id: str,
    step: str,
    body: VersionCreate,
    user: User = Depends(get_current_user),
) -> VersionOut:
    """BR-1/BR-5: insert-only; `parent_version` lets a post-manual-edit
    regenerate track the user-edited version it descends from."""
    async with request.app.state.database.session() as db:
        proj = await _get_project(db, project_id, user.id)
        svc = VersioningService(db)
        sv = await svc.create(
            project_id=proj.id,
            step=step,
            content=body.content,
            actor=body.actor or str(user.id),
            parent_version=body.parent_version,
        )
        await db.commit()
        return _out(sv)


@router.post(
    "/projects/{project_id}/steps/{step}/versions/{version}/restore",
    response_model=RestoreResponse,
)
async def restore_version(
    request: Request,
    project_id: str,
    step: str,
    version: int,
    user: User = Depends(get_current_user),
) -> RestoreResponse:
    async with request.app.state.database.session() as db:
        proj = await _get_project(db, project_id, user.id)
        if proj.status in _RUNNING_STATUSES:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="cannot restore while the project is running a step",
            )
        svc = VersioningService(db)
        target, staled = await svc.restore(
            project_id=proj.id, step=step, version=version, actor=str(user.id)
        )
        await db.commit()
        return RestoreResponse(restored=_out(target), staled_steps=staled)


@router.get(
    "/projects/{project_id}/steps/{step}/versions/compare",
    response_model=CompareResponse,
)
async def compare_versions(
    request: Request,
    project_id: str,
    step: str,
    v1: int = Query(..., alias="from"),
    v2: int = Query(..., alias="to"),
    user: User = Depends(get_current_user),
) -> CompareResponse:
    async with request.app.state.database.session() as db:
        proj = await _get_project(db, project_id, user.id)
        svc = VersioningService(db)
        result = await svc.compare(proj.id, step, v1, v2)
        return CompareResponse(**result)


async def _get_project(db, project_id: str, user_id) -> Project:
    try:
        pid = uuid.UUID(str(project_id))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="project not found") from exc
    res = await db.execute(select(Project).where(Project.id == pid))
    proj = res.scalar_one_or_none()
    if proj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="project not found")
    if str(proj.owner_id) != str(user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="forbidden")
    return proj
