"""Scene endpoints — GET/PUT scenes + per-scene approve (Task 5-1) plus
reorder/add/delete/duplicate (Task 5-4, §6 api-spec).

No business logic here; every route delegates to SceneService.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import get_current_user
from app.models.user import User
from app.services.scene_service import SceneNotFoundError, SceneService
from app.services.scene_validator import SceneValidationError

router = APIRouter(prefix="/projects/{project_id}/scenes", tags=["scenes"])


class ReorderScenesRequest(BaseModel):
    scene_ids: list[str] = Field(min_length=1)


class AddSceneRequest(BaseModel):
    after_scene_number: int = Field(ge=0)
    layout: str


@router.get("")
async def list_scenes(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """GET /projects/{id}/scenes?version=latest — full Scene JSON + `approved`."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        return await svc.list_scenes(project_id)


@router.put("/{scene_id}")
async def update_scene(
    project_id: str,
    scene_id: str,
    payload: dict,
    request: Request,
    user: User = Depends(get_current_user),
):
    """PUT /projects/{id}/scenes/{scene_id} — autosave; 422 with field_path on invalid scene."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.update_scene(
                project_id, scene_id, payload, created_by=user.role
            )
        except SceneValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"field_path": exc.field_path, "message": str(exc)},
            ) from exc
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{scene_id}/approve")
async def approve_scene(
    project_id: str,
    scene_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """POST /projects/{id}/scenes/{scene_id}/approve — per-scene approve (BR-5, not per-step)."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.approve_scene(project_id, scene_id, user_id=str(user.id))
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/reorder")
async def reorder_scenes(
    project_id: str,
    payload: ReorderScenesRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """POST /projects/{id}/scenes/reorder — `{scene_ids}` new order (Task 5-4, BR-1)."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.reorder_scenes(
                project_id, payload.scene_ids, created_by=user.role
            )
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("")
async def add_scene(
    project_id: str,
    payload: AddSceneRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """POST /projects/{id}/scenes — `{after_scene_number, layout}` → new empty-template scene."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.add_scene(
                project_id, payload.after_scene_number, payload.layout, created_by=user.role
            )
        except SceneValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"field_path": exc.field_path, "message": str(exc)},
            ) from exc


@router.delete("/{scene_id}")
async def delete_scene(
    project_id: str,
    scene_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """DELETE /projects/{id}/scenes/{scene_id} (Task 5-4, BR-2)."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.delete_scene(project_id, scene_id, created_by=user.role)
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{scene_id}/duplicate")
async def duplicate_scene(
    project_id: str,
    scene_id: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """POST /projects/{id}/scenes/{scene_id}/duplicate (Task 5-4, BR-4 — new scene_id)."""

    async with request.app.state.database.session() as db:
        svc = SceneService(db)
        try:
            return await svc.duplicate_scene(project_id, scene_id, created_by=user.role)
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
