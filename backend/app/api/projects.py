"""Project CRUD endpoints — FR-01 + summary (task 5-10).

No business logic here; every route delegates to ProjectService except
``GET /projects/{id}/summary`` which delegates to ProjectSummaryService.
Ownership enforcement (🅞) happens in the service layer.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func

from app.core.deps import get_current_user
from app.models.project import Project
from app.models.step_version import StepVersion
from app.models.user import User
from app.schemas.project import (
    LIFECYCLE_GROUPS,
    ProjectCreate,
    ProjectMode,
    ProjectOut,
    ProjectStatus,
    ProjectUpdate,
)
from app.schemas.project_summary import ProjectSummaryOut
from app.services.project_service import ProjectService
from app.services.project_summary import ProjectSummaryService
from app.services.state_machine import TransitionError
from app.services.state_machine_edges import TransitionError as EdgeTransitionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


# ── helpers ───────────────────────────────────────────────────────────────────


async def _enrich(
    project: Project, db, user_id: UUID,
) -> ProjectOut:
    step_count = (await db.execute(
        select(func.count(StepVersion.id)).where(
            StepVersion.project_id == project.id,
            StepVersion.stale.is_(False),
        )
    )).scalar() or 0
    return ProjectOut.from_orm(project, step_count=step_count)


# ── list ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    request: Request,
    archived: bool = Query(False, description="Include archived projects"),
    mode: str | None = Query(None, description="Filter: interactive|daily_news"),
    q: str | None = Query(None, description="Search project name"),
    user: User = Depends(get_current_user),
):
    """List current user's projects (ownership enforced in service)."""
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        rows = await svc.list_for_user(
            user_id=user.id, archived=archived, mode=mode, search=q,
        )
        return [await _enrich(p, db, user.id) for p in rows]


# ── grouped dashboard (BR-6 + BR-7) ──────────────────────────────────────────


@router.get("/groups", response_model=list[dict])
async def list_projects_grouped(
    request: Request,
    archived: bool = Query(False),
    mode: str | None = Query(None, description="all|interactive|daily_news"),
    q: str | None = Query(None),
    user: User = Depends(get_current_user),
):
    """Dashboard: projects grouped by lifecycle; empty groups hidden (BR-6)."""
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        mode_filter = None if (not mode or mode == "all") else mode
        rows = await svc.list_for_user(
            user_id=user.id, archived=archived, mode=mode_filter, search=q,
        )
        enriched = [await _enrich(p, db, user.id) for p in rows]

        buckets: dict[str, list] = {k: [] for k in LIFECYCLE_GROUPS}
        for pj in enriched:
            assigned = False
            for gk, gv in LIFECYCLE_GROUPS.items():
                if pj.status in gv["statuses"]:
                    buckets[gk].append(pj.model_dump(mode="json"))
                    assigned = True
                    break
            if not assigned:
                buckets.setdefault("other", []).append(
                    pj.model_dump(mode="json")
                )

        return [
            {
                "key": k,
                "label": v["label"],
                "order": v["order"],
                "projects": buckets[k],
            }
            for k, v in sorted(
                LIFECYCLE_GROUPS.items(), key=lambda x: x[1]["order"]
            )
            if buckets.get(k)  # hide empty groups (BR-6)
        ]


# ── summary (task 5-10 — NEW endpoint, contract change) ──────────────────────


@router.get("/{project_id}/summary", response_model=ProjectSummaryOut)
async def get_project_summary(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    """Project summary for ProjectDrawer: metadata + AI summary + verdict +
    estimated cost + source count + last 5 activity entries.

    🅞 Ownership enforced — only the project owner (or admin) may access.
    Partial-failure aware: a cost-query exception is caught and the field
    is left at 0 + "không tải được" label (AC-4).
    """
    async with request.app.state.database.session() as db:
        svc = ProjectSummaryService(db)
        summary = await svc.get_summary(project_id, user.id)
        if summary is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        return summary


# ── detail ────────────────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        return await _enrich(proj, db, user.id)


# ── create ────────────────────────────────────────────────────────────────────


@router.post(
    "", response_model=ProjectOut, status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: Request,
    body: ProjectCreate,
    user: User = Depends(get_current_user),
):
    """Create a new project (AC-1)."""
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.create(
            name=body.name,
            topic=body.topic,
            owner_id=user.id,
            mode=body.mode.value,
            formats=body.formats,
            voice_gender=body.voice_gender,
        )
        await db.commit()
        return await _enrich(proj, db, user.id)


# ── update ────────────────────────────────────────────────────────────────────


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    request: Request,
    project_id: UUID,
    body: ProjectUpdate,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        if proj.status not in {
            ProjectStatus.DRAFT,
            ProjectStatus.NEED_REVIEW,
            ProjectStatus.REVISING,
        }:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot edit project in state {proj.status}. "
                    "Only DRAFT / NEED_REVIEW / REVISING are editable."
                ),
            )
        proj = await svc.update(
            proj, **body.model_dump(exclude_none=True)
        )
        await db.commit()
        return await _enrich(proj, db, user.id)


# ── delete (BR-1) ─────────────────────────────────────────────────────────────


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    """Hard-delete DRAFT project with no step versions (BR-1).

    409 if the project has content — hint to use archive.
    """
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        try:
            await svc.delete(proj, actor=str(user.id))
        except (TransitionError, EdgeTransitionError) as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot delete: project is not DRAFT or has step versions. "
                    "Use POST /projects/{id}/archive instead."
                ),
            ) from exc
        await db.commit()


# ── clone (BR-2) ──────────────────────────────────────────────────────────────


@router.post(
    "/{project_id}/clone",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
)
async def clone_project(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    """Clone a project (BR-2): copies latest non-stale steps, excludes renders."""
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        new_proj = await svc.clone(proj, actor=user.id)
        step_copies = await svc.clone_step_versions(proj.id, new_proj.id)
        for sc in step_copies:
            db.add(sc)
        await db.commit()
        return await _enrich(new_proj, db, user.id)


# ── archive / unarchive ───────────────────────────────────────────────────────


@router.post("/{project_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get_any(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        await svc.archive(proj, actor=str(user.id))
        await db.commit()


@router.post("/{project_id}/unarchive", response_model=ProjectOut)
async def unarchive_project(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        svc = ProjectService(db)
        proj = await svc.get_any(project_id, user.id)
        if proj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
        await svc.unarchive(proj, actor=str(user.id))
        await db.commit()
        return await _enrich(proj, db, user.id)


# ── TTS preview endpoint (BR-5, used by Create-project modal) ────────────────


@router.get("/preview/tts", tags=["projects"])
async def tts_preview(
    voice_gender: str = Query("female", pattern="^(female|male)$"),
    user: User = Depends(get_current_user),
):
    """Return a short audio sample for the Create-project modal voice preview.

    The audio is content-addressed and cached for the process lifetime (BR-5).
    """
    from app.adapters.tts.base import ProviderError
    from app.services.tts_preview_service import tts_preview

    try:
        audio_bytes, duration_ms = await tts_preview(voice_gender)
    except ProviderError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"TTS preview unavailable: {exc}",
        ) from exc

    from fastapi.responses import Response

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "X-Duration-Ms": str(duration_ms),
            "Cache-Control": "public, max-age=3600",
        },
    )
