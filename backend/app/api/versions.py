"""Version history endpoints — matches api-spec §3."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.project import Project
from app.models.step_version import StepVersion, _STEP_ORDER
from app.schemas.version import (
    CompareRequest,
    CompareResponse,
    RestoreResponse,
    VersionListResponse,
    VersionOut,
)
from app.core.deps import get_current_user
from app.services.versioning_service import VersioningService

router = APIRouter(tags=["versions"])


@router.get(
    "/projects/{project_id}/steps/{step}/versions",
    response_model=VersionListResponse,
)
async def list_versions(
    project_id: str,
    step: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> VersionListResponse:
    proj = await _get_project(db, project_id, user.id)
    res = await db.execute(
        select(StepVersion)
        .where(StepVersion.project_id == proj.id, StepVersion.step == step)
        .order_by(StepVersion.version.desc())
    )
    versions = [
        VersionOut(
            id=str(v.id),
            version=v.version,
            step=v.step,
            stale=v.stale,
            parent_version=v.parent_version,
            created_by=v.created_by,
            created_at=v.created_at.isoformat(),
        )
        for v in res.scalars().all()
    ]
    return VersionListResponse(versions=versions)


@router.post(
    "/projects/{project_id}/steps/{step}/versions/{version}/restore",
    response_model=RestoreResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_version(
    project_id: str,
    step: str,
    version: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> RestoreResponse:
    proj = await _get_project(db, project_id, user.id)
    sv = VersioningService(db)
    target, staled = await sv.restore(
        project_id=proj.id, step=step, version=version, actor=user.email
    )
    await db.commit()
    return RestoreResponse(
        restored=VersionOut(
            id=str(target.id),
            version=target.version,
            step=target.step,
            stale=target.stale,
            parent_version=target.parent_version,
            created_by=target.created_by,
            created_at=target.created_at.isoformat(),
        ),
        staled_steps=staled,
    )


@router.get(
    "/projects/{project_id}/steps/{step}/versions/compare",
    response_model=CompareResponse,
)
async def compare_versions(
    project_id: str,
    step: str,
    v1: int = Query(..., alias="from"),
    v2: int = Query(..., alias="to"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CompareResponse:
    proj = await _get_project(db, project_id, user.id)
    sv = VersioningService(db)
    result = await sv.compare(proj.id, step, v1, v2)
    return CompareResponse(**result)


async def _get_project(db: AsyncSession, project_id: str, user_id: str) -> Project:
    pid = uuid.UUID(project_id)
    res = await db.execute(select(Project).where(Project.id == pid))
    proj = res.scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    if str(proj.owner_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return proj
