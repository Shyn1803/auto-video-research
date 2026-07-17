"""Project request/response schemas + shared BR-3/BR-6 constants (FR-01, task 1-3).

Single source for ``next_action`` label/href mapping and dashboard lifecycle
grouping — ``app.services.project_service`` and ``app.api.projects`` both
import these rather than each keeping their own copy (rules/code-style.md:
no inline magic strings for status values).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Re-export the canonical status enum — projects use the same lifecycle
# states as the state machine (app.services.state_machine.ProjectStatus).
from app.services.state_machine import ProjectStatus

__all__ = [
    "LIFECYCLE_GROUPS",
    "NEXT_ACTION_MAP",
    "ProjectCreate",
    "ProjectMode",
    "ProjectOut",
    "ProjectStatus",
    "ProjectUpdate",
]


class ProjectMode(StrEnum):
    interactive = "interactive"
    daily_news = "daily_news"


# BR-3: "hành động tiếp theo" suy từ status.
NEXT_ACTION_MAP: dict[str, dict[str, str]] = {
    "DRAFT": {"label": "Tiếp tục chỉnh sửa", "href": "/edit"},
    "RESEARCHING": {"label": "Đang nghiên cứu", "href": "/research"},
    "NEED_REVIEW": {"label": "Mở duyệt ▸", "href": "/review"},
    "REVISING": {"label": "Chỉnh sửa", "href": "/edit"},
    "APPROVED": {"label": "Xem & đăng", "href": "/publish"},
    "PRODUCING": {"label": "Đang sản xuất", "href": "/produce"},
    "RENDERING": {"label": "Đang render", "href": "/render"},
    "READY": {"label": "Xem & đăng", "href": "/publish"},
    "PUBLISHING": {"label": "Đang đăng", "href": "/publish"},
    "PUBLISHED": {"label": "Đã đăng", "href": "/published"},
    "FAILED": {"label": "Xem lỗi & chạy tiếp", "href": "/retry"},
    "ARCHIVED": {"label": "Đã lưu trữ", "href": "/archive"},
}

# BR-6: Dashboard nhóm theo vòng đời, thứ tự Chờ duyệt → Đang chạy → Đang làm dở → Đã đăng.
LIFECYCLE_GROUPS: dict[str, dict[str, Any]] = {
    "waiting_review": {
        "label": "Chờ duyệt",
        "statuses": {"NEED_REVIEW"},
        "order": 0,
    },
    "running": {
        "label": "Đang chạy",
        "statuses": {"RESEARCHING", "PRODUCING", "RENDERING", "PUBLISHING"},
        "order": 1,
    },
    "in_progress": {
        "label": "Đang làm dở",
        "statuses": {"DRAFT", "REVISING", "APPROVED", "FAILED"},
        "order": 2,
    },
    "published": {
        "label": "Đã đăng 7 ngày",
        "statuses": {"PUBLISHED"},
        "order": 3,
    },
}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    topic: str = Field(min_length=1)
    mode: ProjectMode = ProjectMode.interactive
    formats: list[str] | None = None
    voice_gender: str | None = Field(default="female", pattern="^(female|male)$")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    topic: str | None = Field(default=None, min_length=1)
    formats: list[str] | None = None
    voice_gender: str | None = Field(default=None, pattern="^(female|male)$")


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    topic: str
    mode: str
    status: str
    language: str
    formats: list[str]
    voice_id: str | None = None
    voice_gender: str | None = None
    cloned_from: UUID | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    step_count: int = 0
    next_action: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_orm(
        cls,
        project: Any,
        *,
        step_count: int = 0,
        step_progress: dict[str, Any] | None = None,
    ) -> "ProjectOut":
        """Build the response model + derive ``next_action`` server-side (BR-3)."""
        base = NEXT_ACTION_MAP.get(project.status, {"label": "—", "href": "#"})
        action = dict(base)
        if project.status in {"RESEARCHING", "PRODUCING", "RENDERING", "PUBLISHING"} and step_progress:
            pct = step_progress.get("pct", 0)
            step_name = step_progress.get("step", "đang chạy")
            action["label"] = f"● {step_name} {pct}%"

        formats = project.formats
        if isinstance(formats, str):
            # Postgres text[] server_default comes back as a literal like "{a,b}"
            formats = [f for f in formats.strip("{}").split(",") if f]

        return cls(
            id=project.id,
            name=project.name,
            topic=project.topic,
            mode=project.mode,
            status=project.status,
            language=project.language,
            formats=formats or [],
            voice_id=project.voice_id,
            voice_gender=project.voice_gender,
            cloned_from=project.cloned_from,
            archived_at=project.archived_at,
            created_at=project.created_at,
            updated_at=project.updated_at,
            step_count=step_count,
            next_action=action,
        )
