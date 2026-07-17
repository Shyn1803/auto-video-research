"""FR-17 transition matrix — single source of truth for valid project status edges.

Every write to ``projects.status`` *must* flow through the state machine
service (``ProjectStateMachine``), which validates against this table.
Both production code and tests import ``EDGES`` from here so the edge set
is "một nguồn cho code + test + docs" per Task 1-4 Scope.

Source: ``docs/SRS.md`` FR-17, ``docs/specs/database-schema.md`` §2.2.
"""

from __future__ import annotations

# Canonical status values — must match the CHECK constraint in the projects
# table AND the glossary term "status".
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

# All valid statuses in a flat set (useful for validation helpers).
ALL_STATUSES: frozenset[str] = frozenset(
    {
        DRAFT,
        RESEARCHING,
        NEED_REVIEW,
        REVISING,
        APPROVED,
        PRODUCING,
        RENDERING,
        READY,
        PUBLISHING,
        PUBLISHED,
        FAILED,
        ARCHIVED,
    }
)

# ---------------------------------------------------------------------------
# Edge matrix: source → set of allowed target statuses.
#
# Derived from SRS FR-17:
#
#   DRAFT → RESEARCHING → NEED_REVIEW ⇄ REVISING → APPROVED
#   → PRODUCING → RENDERING → READY → PUBLISHING → PUBLISHED
#   Mọi trạng thái → FAILED (resume về trạng thái trước đó)
#   ARCHIVED (từ mọi trạng thái kết thúc)
#
# BUSINESS RULES implemented here:
#   BR-3  FAILED/CANCELLED keep `previous_status`; resume only goes back
#         exactly there (enforced in the service, not in the matrix).
#   BR-4  ARCHIVED only reachable from terminal/stop states
#         (PUBLISHED, FAILED, DRAFT, READY).
#   BR-5  Same-status transition → no-op 200 (service-level; matrix does
#         not list X → X because the service short-circuits before lookup).
# ---------------------------------------------------------------------------

EDGES: dict[str, frozenset[str]] = {
    # ── happy-path linear progression ────────────────────────────────────
    DRAFT: frozenset({RESEARCHING, ARCHIVED, FAILED}),
    RESEARCHING: frozenset({NEED_REVIEW, ARCHIVED, FAILED}),
    NEED_REVIEW: frozenset({REVISING, APPROVED, ARCHIVED, FAILED}),
    REVISING: frozenset({NEED_REVIEW, APPROVED, ARCHIVED, FAILED}),
    APPROVED: frozenset({PRODUCING, ARCHIVED, FAILED}),
    PRODUCING: frozenset({RENDERING, ARCHIVED, FAILED}),
    RENDERING: frozenset({READY, ARCHIVED, FAILED}),
    READY: frozenset({PUBLISHING, ARCHIVED, FAILED}),
    PUBLISHING: frozenset({PUBLISHED, ARCHIVED, FAILED}),
    # ── terminal states ──────────────────────────────────────────────────
    PUBLISHED: frozenset({ARCHIVED, FAILED}),
    # ── error / stop states ──────────────────────────────────────────────
    FAILED: frozenset({ARCHIVED}),  # resume handled via previous_status
    # ── archive is terminal (no outgoing edges via matrix) ──────────────
    ARCHIVED: frozenset(),
}


def allowed_transitions(from_status: str) -> frozenset[str]:
    """Return the set of statuses that *from_status* may transition to.

    Raises ``ValueError`` if *from_status* is not a recognised status.
    """
    if from_status not in ALL_STATUSES:
        raise ValueError(
            f"Unknown status {from_status!r}. "
            f"Valid values: {sorted(ALL_STATUSES)}"
        )
    return EDGES[from_status]


def is_valid_edge(from_status: str, to_status: str) -> bool:
    """Return True if ``from_status → to_status`` is an allowed edge."""
    return to_status in EDGES.get(from_status, frozenset())


def is_terminal(status: str) -> bool:
    """A terminal status has no outgoing transitions in the normal matrix
    (FAILED and ARCHIVED)."""
    return not EDGES.get(status, frozenset())


class TransitionError(ValueError):
    """Raised for an unknown status or a disallowed from→to transition."""


def validate(from_status: str, to_status: str) -> None:
    """Raise ``TransitionError`` unless ``from_status -> to_status`` is a valid edge."""
    if from_status not in ALL_STATUSES:
        raise TransitionError(f"Unknown status {from_status!r}")
    if to_status not in ALL_STATUSES:
        raise TransitionError(f"Unknown status {to_status!r}")
    if not is_valid_edge(from_status, to_status):
        raise TransitionError(f"invalid transition {from_status} -> {to_status}")
