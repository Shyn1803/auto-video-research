"""Pydantic event schemas matching docs/specs/event-catalog.md v1.0.0.

Used by the in-process bus today; NATS JetStream migrates the same models
after Phase 2 with zero call-site changes (AR-5 in ARCHITECTURE.md).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Common wrapper for every event emitted on the bus."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    schema_version: str = "1.0.0"
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str  # = run_id or render_batch_id for the pipeline run
    payload: dict


class ProjectStatusPayload(BaseModel):
    project_id: str
    from_state: str
    to_state: str
    actor: str | None = None
    reason: str | None = None


class StepProgressPayload(BaseModel):
    project_id: str
    run_id: str
    step: str
    pct: int = Field(ge=0, le=100)
    message: str | None = None


def project_status(
    project_id: str,
    from_state: str,
    to_state: str,
    correlation_id: str,
    actor: str | None = None,
    reason: str | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        event_type="project.status",
        correlation_id=correlation_id,
        payload=ProjectStatusPayload(
            project_id=project_id,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
        ).model_dump(),
    )


def step_progress(
    project_id: str,
    run_id: str,
    step: str,
    pct: int,
    correlation_id: str,
    message: str | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        event_type="step.progress",
        correlation_id=correlation_id,
        payload=StepProgressPayload(
            project_id=project_id,
            run_id=run_id,
            step=step,
            pct=pct,
            message=message,
        ).model_dump(),
    )
