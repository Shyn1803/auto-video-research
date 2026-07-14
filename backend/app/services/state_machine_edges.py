"""FR-17 transition matrix as data.

Single truth source for allowed transitions — code, tests, and docs
all import EDGES from here (xem Task 1-4).
"""
from __future__ import annotations

from app.services.state_machine import ProjectStatus, _EdgesMeta, _edges_for

EDGES: dict[str, set[str]] = _EdgesMeta.edges  # re-export for test/doc import


def validate(from_status: str, to_status: str) -> None:
    allowed = _edges_for(from_status)
    if to_status not in allowed:
        if from_status == to_status:
            return  # idempotent no-op
        from app.services.state_machine import TransitionError
        raise TransitionError(
            f"Invalid transition {from_status!r} -> {to_status!r}. "
            f"Allowed targets: {sorted(allowed) or '(none)'}"
        )
