"""Scene service — GET/PUT scenes + per-scene approve (Task 5-1, FR-09) plus
reorder/add/delete/duplicate (Task 5-4, FR-09, api-spec.md §6).

Scenes live inside the ``scene_set`` step_version content (insert-only, see
``app.models.step_version``). Approval is intentionally NOT stored in that
JSON (see ``app.models.scene_approval`` docstring) — it is UI/workflow state,
joined in at read time.

Every op below (reorder/add/delete/duplicate) inserts a brand-new
``scene_set`` StepVersion (BR-3 — "mọi op = version mới"; there is no
separate undo stack, restoring an older version is the undo path, 5-9).
Reorder/add/delete only ever touch ``scene_number`` — every existing
``scene_id`` is preserved (BR-1). Duplicate mints a brand-new ``scene_id``
(BR-4) so its cache key differs from the original's.
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

    async def _commit_new_version(
        self,
        project_id: str,
        prev_version: StepVersion | None,
        scenes: list[dict[str, Any]],
        *,
        created_by: str,
    ) -> StepVersion:
        """Insert-only: never UPDATE an existing scene_set row (BR-3)."""

        new_version = StepVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            step="scene_set",
            version=(prev_version.version + 1) if prev_version else 1,
            parent_version=prev_version.version if prev_version else None,
            content={"scenes": scenes},
            stale=False,
            created_by=created_by,
        )
        self.db.add(new_version)
        await self.db.flush()
        return new_version

    async def reorder_scenes(
        self, project_id: str, scene_ids: list[str], *, created_by: str
    ) -> list[dict[str, Any]]:
        """Reorder by a full new ordering of scene_ids — BR-1: only `scene_number`
        changes, every `scene_id` is preserved."""

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            raise SceneNotFoundError(f"no scene_set exists for project {project_id}")

        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        by_id = {s["scene_id"]: s for s in scenes}
        if set(scene_ids) != set(by_id):
            raise SceneNotFoundError("scene_ids must be a permutation of the current scene set")

        reordered = [by_id[sid] for sid in scene_ids]
        reordered = _renumber(reordered)
        await self._commit_new_version(project_id, version, reordered, created_by=created_by)
        return reordered

    async def add_scene(
        self, project_id: str, after_scene_number: int, layout: str, *, created_by: str
    ) -> dict[str, Any]:
        """Insert a new (empty-template) scene right after `after_scene_number`
        (0 = insert at the start)."""

        version = await self._latest_scene_set_version(project_id)
        scenes: list[dict[str, Any]] = list(version.content.get("scenes", [])) if version else []

        template = {
            "scene_id": str(uuid.uuid4()),
            "schema_version": "1.0.0",
            "scene_number": 1,  # placeholder — _renumber() below sets the real value
            "duration_ms": 5000,
            "layout": layout,
            "background": {"type": "color", "color": "#0F172A"},
            "texts": [
                {
                    "id": "t1",
                    "content": "Nội dung mới",
                    "role": "heading",
                    "position": "center",
                }
            ],
            "images": [],
            "subtitle": {"enabled": True, "style": "line"},
            "transition": {"type": "none", "duration_ms": 300},
        }
        try:
            validated = Scene.model_validate(template)
        except Exception as exc:
            raise SceneValidationError(_first_error_field(exc), str(exc)) from exc

        new_scene = validated.model_dump(mode="json", by_alias=True)
        insert_at = max(0, min(after_scene_number, len(scenes)))
        scenes.insert(insert_at, new_scene)
        scenes = _renumber(scenes)

        await self._commit_new_version(project_id, version, scenes, created_by=created_by)
        return next(s for s in scenes if s["scene_id"] == new_scene["scene_id"])

    async def delete_scene(
        self, project_id: str, scene_id: str, *, created_by: str
    ) -> dict[str, Any]:
        """Remove a scene (BR-2: caller states the duration impact before
        calling this — see sceneOpsReducer.deleteImpactMessage on the FE)."""

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            raise SceneNotFoundError(f"no scene_set exists for project {project_id}")

        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        idx = next((i for i, s in enumerate(scenes) if s["scene_id"] == scene_id), None)
        if idx is None:
            raise SceneNotFoundError(f"scene {scene_id} not found")

        removed_duration_ms = scenes[idx].get("duration_ms", 0)
        scenes = [s for i, s in enumerate(scenes) if i != idx]
        scenes = _renumber(scenes)

        await self._commit_new_version(project_id, version, scenes, created_by=created_by)
        return {
            "deleted_scene_id": scene_id,
            "removed_duration_ms": removed_duration_ms,
            "scenes": scenes,
        }

    async def duplicate_scene(
        self, project_id: str, scene_id: str, *, created_by: str
    ) -> dict[str, Any]:
        """BR-4: the copy gets a brand-new scene_id (cache key differs);
        content is otherwise identical, inserted right after the original."""

        version = await self._latest_scene_set_version(project_id)
        if version is None:
            raise SceneNotFoundError(f"no scene_set exists for project {project_id}")

        scenes: list[dict[str, Any]] = list(version.content.get("scenes", []))
        idx = next((i for i, s in enumerate(scenes) if s["scene_id"] == scene_id), None)
        if idx is None:
            raise SceneNotFoundError(f"scene {scene_id} not found")

        new_scene_id = str(uuid.uuid4())
        copy = {**scenes[idx], "scene_id": new_scene_id}
        scenes.insert(idx + 1, copy)
        scenes = _renumber(scenes)

        await self._commit_new_version(project_id, version, scenes, created_by=created_by)
        return next(s for s in scenes if s["scene_id"] == new_scene_id)


def _renumber(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Set `scene_number` to 1..n in list order — every `scene_id` untouched (BR-1)."""

    return [{**s, "scene_number": i + 1} for i, s in enumerate(scenes)]


def _first_error_field(exc: Exception) -> str:
    """Best-effort field_path extraction from a pydantic ValidationError."""

    errors = getattr(exc, "errors", None)
    if callable(errors):
        parsed = errors()
        if parsed:
            loc = parsed[0].get("loc", ())
            return ".".join(str(p) for p in loc) or "scene"
    return "scene"
