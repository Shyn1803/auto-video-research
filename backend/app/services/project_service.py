"""Project CRUD + next_action + ownership enforcement."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.status_history import StatusHistory
from app.services.state_machine import ProjectStateMachine

logger = logging.getLogger(__name__)

NEXT_ACTION_MAP = {
    "NEED_REVIEW": {"label": "Mở duyệt ▸", "href": "/review"},
    "RESEARCHING": {"label": "Đang nghiên cứu", "href": "/research"},
    "PRODUCING": {"label": "Đang sản xuất", "href": "/produce"},
    "READY": {"label": "Xem & đăng", "href": "/publish"},
    "FAILED": {"label": "Xem lỗi & chạy tiếp", "href": "/retry"},
    "DRAFT": {"label": "Tiếp tục chỉnh sửa", "href": "/edit"},
    "REVISING": {"label": "Chỉnh sửa", "href": "/edit"},
    "RENDERING": {"label": "Đang render", "href": "/render"},
    "PUBLISHING": {"label": "Đang đăng", "href": "/publish"},
    "PUBLISHED": {"label": "Đã đăng", "href": "/published"},
    "ARCHIVED": {"label": "Đã lưu trữ", "href": "/archive"},
}

LIFECYCLE_GROUPS = {
    "waiting_review": {"label": "Chờ duyệt", "statuses": {"NEED_REVIEW"}, "order": 0},
    "running": {"label": "Đang chạy", "statuses": {"RESEARCHING", "PRODUCING", "RENDERING", "PUBLISHING"}, "order": 1},
    "in_progress": {"label": "Đang làm dở", "statuses": {"DRAFT", "REVISING"}, "order": 2},
    "published": {"label": "Đã đăng 7 ngày", "statuses": {"PUBLISHED"}, "order": 3},
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

    async def create(self, *, name: str, topic: str, owner_id: UUID, mode: str = "interactive",
                     formats: list[str] | None = None, voice_id: str | None = None,
                     voice_gender: str | None = None) -> Project:
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

    async def list_for_user(self, user_id: UUID, *, archived: bool = False, mode: str | None = None,
                           search: str | None = None) -> Sequence[Project]:
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
        if project.status != "DRAFT":
            from app.services.state_machine import TransitionError
            raise TransitionError("cannot delete non-DRAFT project — archive instead")
        step_count = await self._db.execute(
            select(func.count(StepVersion.id)).where(StepVersion.project_id == project.id)
        )
        if step_count.scalar() > 0:
            from app.services.state_machine import TransitionError
            raise TransitionError("project has versions — archive instead")
        await self._db.delete(project)
        await self._db.flush()

    async def clone(self, project: Project, actor: UUID) -> Project:
        new = Project(
            name=f"{project.name} (bản sao)",
            topic=project.topic,
            mode=project.mode,
            owner_id=actor,
            formats=project.formats,
            voice_id=project.voice_id,
            voice_gender=project.voice_gender,
            status="DRAFT",
        )
        self._db.add(new)
        await self._db.flush()
        return new

    async def archive(self, project: Project, actor: str) -> Project:
        from app.services.state_machine import ProjectStatus
        if project.status not in {ProjectStatus.PUBLISHED, ProjectStatus.FAILED, ProjectStatus.DRAFT, ProjectStatus.READY}:
            from app.services.state_machine import TransitionError
            raise TransitionError("cannot archive from active states")
        project.archived_at = datetime.now(timezone.utc)
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
