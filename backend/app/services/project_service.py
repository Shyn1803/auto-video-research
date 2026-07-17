"""Project CRUD + next_action + ownership enforcement (FR-01, task 1-3).

``NEXT_ACTION_MAP`` / ``LIFECYCLE_GROUPS`` live in ``app.schemas.project`` —
single source shared with the API layer's response building.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.step_version import StepVersion
from app.schemas.project import LIFECYCLE_GROUPS, NEXT_ACTION_MAP
from app.services.state_machine import ProjectStateMachine, ProjectStatus, TransitionError

logger = logging.getLogger(__name__)

# Statuses a project may be archived from (BR-4: archive read-only afterwards).
_ARCHIVABLE_STATUSES = {
    ProjectStatus.DRAFT,
    ProjectStatus.READY,
    ProjectStatus.PUBLISHED,
    ProjectStatus.FAILED,
}


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._sm = ProjectStateMachine()

    async def get(self, project_id: UUID, user_id: UUID) -> Project | None:
        """Get a non-archived project owned by user_id (ownership enforcement)."""
        result = await self._db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
                Project.archived_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_any(self, project_id: UUID, user_id: UUID) -> Project | None:
        """Get an owned project regardless of archived state (needed for unarchive)."""
        result = await self._db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        topic: str,
        owner_id: UUID,
        mode: str = "interactive",
        formats: list[str] | None = None,
        voice_id: str | None = None,
        voice_gender: str | None = None,
    ) -> Project:
        proj = Project(
            name=name,
            topic=topic,
            mode=mode,
            owner_id=owner_id,
            formats=formats or ["vertical_1080x1920"],
            voice_id=voice_id,
            voice_gender=voice_gender,
        )
        self._db.add(proj)
        await self._db.flush()
        return proj

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        archived: bool = False,
        mode: str | None = None,
        search: str | None = None,
    ) -> Sequence[Project]:
        q = select(Project).where(Project.owner_id == user_id)
        if not archived:
            q = q.where(Project.archived_at.is_(None))
        if mode and mode != "all":
            q = q.where(Project.mode == mode)
        if search:
            q = q.where(Project.name.ilike(f"%{search}%"))
        q = q.order_by(Project.updated_at.desc())
        result = await self._db.execute(q)
        return result.scalars().all()

    async def update(self, project: Project, **kwargs) -> Project:
        for k, v in kwargs.items():
            if hasattr(project, k) and v is not None:
                setattr(project, k, v)
        project.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return project

    async def delete(self, project: Project, actor: str = "user") -> None:
        """Hard-delete a DRAFT project with no step versions (BR-1).

        Raises TransitionError (mapped to 409 by the router) otherwise —
        the caller is pointed at archive instead.
        """
        if project.status != ProjectStatus.DRAFT:
            raise TransitionError("cannot delete non-DRAFT project — archive instead")
        step_count_result = await self._db.execute(
            select(func.count(StepVersion.id)).where(StepVersion.project_id == project.id)
        )
        if (step_count_result.scalar() or 0) > 0:
            raise TransitionError("project has versions — archive instead")
        await self._db.delete(project)
        await self._db.flush()

    async def clone(self, project: Project, actor: UUID) -> Project:
        """Clone project metadata (BR-2). Step-version copy is a separate call
        (``clone_step_versions``) so tests can assert each concern independently."""
        new = Project(
            name=f"{project.name} (bản sao)",
            topic=project.topic,
            mode=project.mode,
            owner_id=actor,
            formats=project.formats,
            voice_id=project.voice_id,
            voice_gender=project.voice_gender,
            status=ProjectStatus.DRAFT,
            cloned_from=project.id,
        )
        self._db.add(new)
        await self._db.flush()
        return new

    async def clone_step_versions(
        self, source_project_id: UUID, dest_project_id: UUID
    ) -> list[StepVersion]:
        """Copy the latest non-stale version of every step (BR-2).

        Excludes renders/publishes per scope, resets ``version`` to 1 and
        ``parent_version`` to ``None`` in the new project's own version
        lineage (the clone starts a fresh history, not a shared one).
        """
        result = await self._db.execute(
            select(StepVersion).where(
                StepVersion.project_id == source_project_id,
                StepVersion.stale.is_(False),
                StepVersion.step.not_in(("render", "publish")),
            )
        )
        latest_by_step: dict[str, StepVersion] = {}
        for sv in result.scalars().all():
            current = latest_by_step.get(sv.step)
            if current is None or sv.version > current.version:
                latest_by_step[sv.step] = sv

        copies: list[StepVersion] = []
        for step, sv in latest_by_step.items():
            copies.append(
                StepVersion(
                    project_id=dest_project_id,
                    step=step,
                    version=1,
                    parent_version=None,
                    content=sv.content,
                    stale=False,
                    created_by="clone",
                )
            )
        return copies

    async def archive(self, project: Project, actor: str) -> Project:
        if project.status not in _ARCHIVABLE_STATUSES:
            raise TransitionError("cannot archive from active states")
        project.archived_at = datetime.now(timezone.utc)
        await self._db.flush()
        return project

    async def unarchive(self, project: Project, actor: str) -> Project:
        """Restore an archived project to DRAFT visibility (BR-4)."""
        project.archived_at = None
        await self._db.flush()
        return project


def next_action(status: str, step_progress: dict | None = None) -> dict:
    base = NEXT_ACTION_MAP.get(status, {"label": "—", "href": "#"})
    if status in {"RESEARCHING", "PRODUCING", "RENDERING", "PUBLISHING"} and step_progress:
        pct = step_progress.get("pct", 0)
        step_name = step_progress.get("step", "đang chạy")
        return {**base, "label": f"● {step_name} {pct}%"}
    return base


def group_by_lifecycle(projects: Sequence[Project]) -> dict[str, list[Project]]:
    buckets: dict[str, list[Project]] = {k: [] for k in LIFECYCLE_GROUPS}
    for p in projects:
        assigned = False
        for gk, gv in LIFECYCLE_GROUPS.items():
            if p.status in gv["statuses"]:
                buckets[gk].append(p)
                assigned = True
                break
        if not assigned:
            buckets.setdefault("other", []).append(p)
    return {k: v for k, v in buckets.items() if v}
