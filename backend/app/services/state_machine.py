"""Project state machine — FR-17 transition service.

Writes to projects.status + status_history table; emits project.status
event on every successful transition.
"""
from __future__ import annotations

import logging
from collections.abc import MutableMapping
from enum import StrEnum

from app.events.bus import publish
from app.events.schemas import project_status
from app.services.state_machine_edges import EDGES, TransitionError, validate

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


ABNORMAL_EDGES = {f"{a}->{ProjectStatus.FAILED}" for a in [
    ProjectStatus.RESEARCHING, ProjectStatus.NEED_REVIEW, ProjectStatus.REVISING,
    ProjectStatus.APPROVED, ProjectStatus.PRODUCING, ProjectStatus.RENDERING,
    ProjectStatus.PUBLISHING, ProjectStatus.PUBLISHED,
]}
ABNORMAL_EDGES.add(f"{ProjectStatus.APPROVED}->{ProjectStatus.REVISING}")
ABNORMAL_EDGES.add("ARCHIVED->*")
ABNORMAL_EDGES.add("*->ARCHIVED")


def _edges_for(status: str) -> set[str]:
    return EDGES.get(status, set())


class ProjectStateMachine:
    """Validate and record a project-status transition (FR-17).

    The only module allowed to write ``projects.status``.
    Idempotent: same-state call is a no-op (200, no new history row).
    """

    def __init__(self, bus: MutableMapping[str, object] | None = None) -> None:
        self._bus = bus

    async def transition(
        self,
        project,
        to_state: str,
        actor: str,
        reason: str | None = None,
        session=None,
    ) -> None:
        from_state = project.status
        correlation_id = str(project.id)

        # Idempotent: same target -> no-op unless it's a side-effect edge
        if from_state == to_state:
            return

        validate(from_state, to_state)

        edge_key = f"{from_state}->{to_state}"
        is_abnormal = (
            edge_key in ABNORMAL_EDGES
            or "ARCHIVED" in (from_state, to_state)
        )

        if is_abnormal and not reason:
            raise TransitionError(
                "reason is required for abnormal transitions"
            )

        project.status = to_state

        from app.models.status_history import StatusHistory
        history_row = StatusHistory(
            project_id=project.id,
            from_status=from_state,
            to_status=to_state,
            actor=actor,
            reason=reason,
        )
        session.add(history_row)

        await self._emit(from_state, to_state, correlation_id, actor, reason)
        logger.info(
            "transition %s %s->%s actor=%s",
            project.id, from_state, to_state, actor,
        )

    async def _emit(self, from_state: str, to_state: str,
              correlation_id: str, actor: str | None,
              reason: str | None) -> None:
        try:
            await publish(
                "project.status",
                project_status(
                    project_id=correlation_id,
                    from_state=from_state,
                    to_state=to_state,
                    correlation_id=correlation_id,
                    actor=actor,
                    reason=reason,
                ).model_dump(),
            )
        except Exception:
            logger.debug(
                "event bus unavailable for project.status %s", correlation_id
            )
