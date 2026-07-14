"""FR-17 transition matrix as data.

Single truth source for allowed transitions — code, tests, and docs
all import EDGES and TransitionError from here (Task 1-4).
"""
from __future__ import annotations


class TransitionError(ValueError):
    """Raised when a state transition violates the FR-17 edge matrix."""
    pass


class _EdgesMeta(type):
    """Metaclass-based edge matrix — mirrors state_machine.ProjectStatus."""
    edges: dict[str, set[str]] = {
        "DRAFT": {"RESEARCHING"},
        "RESEARCHING": {"NEED_REVIEW", "FAILED"},
        "NEED_REVIEW": {"APPROVED", "REVISING", "FAILED"},
        "REVISING": {"NEED_REVIEW", "APPROVED", "FAILED"},
        "APPROVED": {"PRODUCING", "REVISING", "FAILED"},
        "PRODUCING": {"RENDERING", "FAILED"},
        "RENDERING": {"READY", "FAILED"},
        "READY": {"PUBLISHING", "FAILED"},
        "PUBLISHING": {"PUBLISHED", "FAILED"},
        "PUBLISHED": {"ARCHIVED", "FAILED"},
        "FAILED": {
            "RESEARCHING", "NEED_REVIEW", "REVISING", "APPROVED",
            "PRODUCING", "RENDERING", "READY", "PUBLISHING",
        },
        "ARCHIVED": set(),  # terminal state — no outgoing edges
    }


EDGES: dict[str, set[str]] = _EdgesMeta.edges


def validate(from_status: str, to_status: str) -> None:
    """Raise TransitionError if to_status is not in the allowed set."""
    allowed = EDGES.get(from_status, set())
    if to_status not in allowed:
        if from_status == to_status:
            return  # idempotent no-op
        raise TransitionError(
            f"Invalid transition {from_status!r} -> {to_status!r}. "
            f"Allowed targets: {sorted(allowed) or '(none)'}"
        )
