"""Pydantic event schemas matching docs/specs/event-catalog.md v1.0.0."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    schema_version: str = "1.0.0"
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str
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