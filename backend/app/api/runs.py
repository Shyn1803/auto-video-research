"""Pipeline run endpoints -- Task 4-1 Step 5 (api-spec §2).

No business logic here (rules/code-style.md) -- every route delegates to
RunService, which owns BR-1/BR-2 enforcement.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_current_user
from app.models.user import User
from app.pipeline.state import NodeName
from app.services.project_service import ProjectService
from app.services.run_service import RunConflictError, RunService

router = APIRouter(prefix="/projects", tags=["runs"])


def _parse_step(step: str) -> NodeName:
    try:
        return NodeName(step)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"unknown step {step!r}; valid: {[n.value for n in NodeName]}",
        ) from exc


@router.post("/{project_id}/steps/{step}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_step(
    request: Request,
    project_id: UUID,
    step: str,
    user: User = Depends(get_current_user),
):
    node = _parse_step(step)
    async with request.app.state.database.session() as db:
        proj_svc = ProjectService(db)
        project = await proj_svc.get(project_id, user.id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

        run_svc = RunService(db, checkpointer=getattr(request.app.state, "checkpointer", None))
        try:
            run = await run_svc.start_run(project, node, actor=str(user.id))
        except RunConflictError as exc:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        await db.commit()
        return {"run_id": str(run.id), "status": run.status}


@router.post("/{project_id}/steps/{step}/approve", status_code=status.HTTP_200_OK)
async def approve_step(
    request: Request,
    project_id: UUID,
    step: str,
    user: User = Depends(get_current_user),
):
    node = _parse_step(step)
    async with request.app.state.database.session() as db:
        proj_svc = ProjectService(db)
        project = await proj_svc.get(project_id, user.id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

        run_svc = RunService(db, checkpointer=getattr(request.app.state, "checkpointer", None))
        active_run = await run_svc.get_active_run(project.id)
        if active_run is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"no active run for project {project_id}"
            )
        try:
            run = await run_svc.approve(project, active_run, node, actor=str(user.id))
        except RunConflictError as exc:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        await db.commit()
        return {"run_id": str(run.id), "status": run.status}


@router.get("/{project_id}/runs/{run_id}")
async def get_run(
    request: Request,
    project_id: UUID,
    run_id: UUID,
    user: User = Depends(get_current_user),
):
    async with request.app.state.database.session() as db:
        proj_svc = ProjectService(db)
        project = await proj_svc.get(project_id, user.id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

        run_svc = RunService(db)
        run = await run_svc.get_run(run_id)
        if run is None or run.project_id != project.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
        return {
            "run_id": str(run.id),
            "project_id": str(run.project_id),
            "status": run.status,
            "current_node": run.current_node,
            "interrupted_node": run.interrupted_node,
            "retry_count": run.retry_count,
            "error": run.error,
            "cancelling": run.status in ("pending", "running", "interrupted")
            and run.cancel_requested_at is not None,
        }


@router.post("/{project_id}/runs/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_run(
    request: Request,
    project_id: UUID,
    run_id: UUID,
    user: User = Depends(get_current_user),
):
    """Task 4-7 Step 2 -- best-effort abort-after-current-node (BR-1, BR-4)."""
    async with request.app.state.database.session() as db:
        proj_svc = ProjectService(db)
        project = await proj_svc.get(project_id, user.id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")

        run_svc = RunService(db, checkpointer=getattr(request.app.state, "checkpointer", None))
        run = await run_svc.get_run(run_id)
        if run is None or run.project_id != project.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")

        try:
            run = await run_svc.cancel_run(project, run, actor=str(user.id))
        except RunConflictError as exc:
            await db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        await db.commit()
        return {"run_id": str(run.id), "status": run.status, "cancelling": True}
