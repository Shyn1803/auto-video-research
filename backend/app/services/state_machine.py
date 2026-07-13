"""Project state machine — FR-17 transition service.

Publishes a "project.status" event via the in-process bus on every
successful transition so the frontend can track progress in real time.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from enum import StrEnum
from typing import ClassVar

from app.events.bus import publish
from app.events.schemas import project_status

logger = logging.getLogger(__name__)


class ProjectStatus(StrEnum):
    DRAFT = "DRAFT"
    RESEARCHING = "RESEARCHING"
    NEED_REVIEW = "NEED_REVIEW"
    REVISING = "REVISING"
    APPROVED = "APPROVED"
    PRODUCING = "PRODUCING"
    RENDERING = "RENDERING"
    READY = "READY"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class _EdgesMeta(type):
    edges: ClassVar[dict[str, set[str]]] = {
        ProjectStatus.DRAFT: {ProjectStatus.RESEARCHING, ProjectStatus.ARCHIVED},
        ProjectStatus.RESEARCHING: {ProjectStatus.NEED_REVIEW, ProjectStatus.FAILED},
        ProjectStatus.NEED_REVIEW: {
            ProjectStatus.APPROVED,
            ProjectStatus.REVISING,
        },
        ProjectStatus.REVISING: {
            ProjectStatus.NEED_REVIEW,
            ProjectStatus.APPROVED,
        },
        ProjectStatus.APPROVED: {
            ProjectStatus.PRODUCING,
            ProjectStatus.REVISING,
            ProjectStatus.FAILED,
        },
        ProjectStatus.PRODUCING: {ProjectStatus.RENDERING, ProjectStatus.FAILED},
        ProjectStatus.RENDERING: {ProjectStatus.READY, ProjectStatus.FAILED},
        ProjectStatus.READY: {ProjectStatus.PUBLISHING, ProjectStatus.ARCHIVED},
        ProjectStatus.PUBLISHING: {ProjectStatus.PUBLISHED, ProjectStatus.FAILED},
        ProjectStatus.PUBLISHED: {ProjectStatus.ARCHIVED},
        ProjectStatus.FAILED: set(),
        ProjectStatus.ARCHIVED: set(),
    }


class EDGES(metaclass=_EdgesMeta):
    pass


def _edges_for(status: str) -> set[str]:
    return EDGES.edges.get(status, set())


class ProjectStateMachine:
    """Validate and record a project-status transition (FR-17).

    Every successful call publishes "project.status" on the in-process bus
    with a full EventEnvelope (BR-1).
    """

    def __init__(self, bus: MutableMapping[str, object] | None = None) -> None:
        self._bus = bus

    async def transition(
        self,
        project_id: str,
        from_state: str,
        to_state: str,
        correlation_id: str,
        actor: str = "system",
        reason: str | None = None,
    ) -> None:
        allowed = _edges_for(from_state)
        if to_state not in allowed:
            if from_state == to_state:
                return
            raise TransitionError(
                f"Invalid transition {from_state!r} -> {to_state!r}. "
                f"Allowed targets: {sorted(allowed) or '(none)'}"
            )
        await publish(
            "project.status",
            project_status(
                project_id=project_id,
                from_state=from_state,
                to_state=to_state,
                correlation_id=correlation_id,
                actor=actor,
                reason=reason,
            ).model_dump(),
        )


class TransitionError(ValueError):
    pass
