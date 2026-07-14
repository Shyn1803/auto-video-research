"""Project status event emitter — lightweight shim used by the state machine.

Transport is the in-process bus during Phase 1; Phase 2 (NATS JetStream)
swaps the import in one place without touching call-sites (AR-5).
"""
from __future__ import annotations

from app.events.bus import publish
from app.events.schemas import project_status


def emit(project_id: str, from_state: str, to_state: str, correlation_id: str, actor: str | None = None, reason: str | None = None) -> None:
    envelope = project_status(
        project_id=project_id,
        from_state=from_state,
        to_state=to_state,
        correlation_id=correlation_id,
        actor=actor,
        reason=reason,
    )
    publish("project.status", envelope.model_dump())
