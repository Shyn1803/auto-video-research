"""Scene service — GET/PUT scenes + per-scene approve (Task 5-1, FR-09).

Scenes live inside the ``scene_set`` step_version content (insert-only, see
``app.models.step_version``). Approval is intentionally NOT stored in that
JSON (see ``app.models.scene_approval`` docstring) — it is UI/workflow state,
joined in at read time.

Scene CRUD ops beyond GET/PUT (create/delete/duplicate/reorder) are task 5-4
scope — not implemented here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene_approval import SceneApproval
from app.models.step_version import StepVersion
from app.schemas.scene import Scene
from app.services.scene_validator import SceneValidationError


class SceneNotFoundError(ValueError):
    """Raised when a scene_id doesn't exist in the current scene_set."""


class SceneService:
    """Reads/writes scenes for a project; owns the approve workflow (BR-5)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _latest_scene_set_version(self, project_id: str) -> StepVersion | None:
        result = await self.db.execute(
            select(StepVersion)
            .where(
                StepVersion.project_id == project_id,
                StepVersion.step == "scene_set",
                StepVersion.stale.is_(False),
            )
            .order_by(StepVersion.version.desc())
        )
        rows = result.scalars().all()
        return rows[0] if rows else None

    async def _approvals_by_scene_id(self, project_id: str) -> dict[str, SceneApproval]:
        result = await self.db.execute(
            select(SceneApproval).where(SceneApproval.project_id == project_id)
        )
        rows = result.scalars().all()
        return {row.scene_id: row for row in rows}

    async def list_scenes(self, project_id: str) -> list[dict[str, Any]]:
        """Return every scene in the current (latest non-stale) scene_set, with `approved`."""

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            return []
        approvals = await self._approvals_by_scene_id(project_id)
        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        out = []
        for scene in scenes:
            approval = approvals.get(scene["scene_id"])
            out.append({**scene, "approved": bool(approval and approval.approved)})
        return out

    async def update_scene(
        self, project_id: str, scene_id: str, payload: dict[str, Any], *, created_by: str
    ) -> dict[str, Any]:
        """Validate + persist an edited scene as a new scene_set version (autosave, BR-3).

        Editing a scene clears its `approved` flag — an edit invalidates a prior
        review per the "duyệt theo từng cảnh" decision (a stale scene shouldn't
        silently stay approved). This mirrors the cascade-stale principle already
        used for step_versions (rules/error-handling.md).
        """

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            raise SceneNotFoundError(f"no scene_set exists for project {project_id}")

        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        idx = next((i for i, s in enumerate(scenes) if s["scene_id"] == scene_id), None)
        if idx is None:
            raise SceneNotFoundError(f"scene {scene_id} not found")

        merged = {**scenes[idx], **payload, "scene_id": scene_id}
        try:
            validated = Scene.model_validate(merged)
        except Exception as exc:  # pydantic ValidationError -> 422 field_path at API layer
            raise SceneValidationError(_first_error_field(exc), str(exc)) from exc

        scenes[idx] = validated.model_dump(mode="json", by_alias=True)

        new_version = StepVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            step="scene_set",
            version=version.version + 1,
            parent_version=version.version,
            content={"scenes": scenes},
            stale=False,
            created_by=created_by,
        )
        self.db.add(new_version)

        # Edit invalidates prior approval (see docstring).
        approvals = await self._approvals_by_scene_id(project_id)
        existing = approvals.get(scene_id)
        if existing is not None and existing.approved:
            existing.approved = False
            existing.approved_at = None
            self.db.add(existing)

        await self.db.flush()
        return {**scenes[idx], "approved": False}

    async def approve_scene(
        self, project_id: str, scene_id: str, *, user_id: str
    ) -> dict[str, Any]:
        """Mark one scene approved (BR-5: per-scene, not per-step)."""

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            raise SceneNotFoundError(f"no scene_set exists for project {project_id}")
        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        if not any(s["scene_id"] == scene_id for s in scenes):
            raise SceneNotFoundError(f"scene {scene_id} not found")

        approvals = await self._approvals_by_scene_id(project_id)
        row = approvals.get(scene_id)
        now = datetime.now(UTC)
        if row is None:
            row = SceneApproval(
                id=str(uuid.uuid4()),
                project_id=project_id,
                scene_id=scene_id,
                approved=True,
                approved_at=now,
                approved_by=user_id,
            )
        else:
            row.approved = True
            row.approved_at = now
            row.approved_by = user_id
        self.db.add(row)
        await self.db.flush()
        return {"scene_id": scene_id, "approved": True, "approved_at": now.isoformat()}


def _first_error_field(exc: Exception) -> str:
    """Best-effort field_path extraction from a pydantic ValidationError."""

    errors = getattr(exc, "errors", None)
    if callable(errors):
        parsed = errors()
        if parsed:
            loc = parsed[0].get("loc", ())
            return ".".join(str(p) for p in loc) or "scene"
    return "scene"
