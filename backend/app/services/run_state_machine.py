"""PipelineRun.status transition matrix -- Task 4-7 Step 1.

Task 4-7's brief talks about "extending 1-4's matrix" with a
RUNNING -> CANCELLED edge, but ``app/services/state_machine.py``
(``ProjectStateMachine``) governs ``projects.status`` (DRAFT/RESEARCHING/
NEED_REVIEW/.../ARCHIVED per docs/specs/database-schema.md's CHECK
constraint) -- that enum has no RUNNING or CANCELLED value at all. RUNNING
and CANCELLED are values of ``PipelineRun.status`` instead (``RunStatus`` in
app/pipeline/state.py: pending/running/interrupted/approved/completed/
failed/cancelled, per the ``ck_pipeline_runs_status`` CHECK constraint added
by migration 008 in Task 4-1). This module is the run-level equivalent of
``state_machine_edges.py``, kept separate rather than folded into it so the
two independently-versioned status columns are never conflated.

Mirrors 4-1 BR-4's own FAILED handling (run.previous_status is set by the
caller in RunService, the same pattern as the existing FAILED transition in
run_service.py -- this module only validates the edge is legal).
"""

from __future__ import annotations

from app.models.pipeline_run import ACTIVE_RUN_STATUSES


class RunTransitionError(ValueError):
    """Raised when a PipelineRun.status transition is not permitted."""


def validate_cancel_edge(from_status: str) -> None:
    """A run can move to CANCELLED only from an active status (pending,
    running, interrupted) -- BR-4: cancelling an already-terminal run
    (completed/failed/cancelled) is invalid and must surface as 409."""
    if from_status not in ACTIVE_RUN_STATUSES:
        raise RunTransitionError(
            f"cannot cancel run in terminal status {from_status!r}"
        )


def validate_resume_edge(from_status: str) -> None:
    """Only a CANCELLED run can be "reopened" by Step 5's resume-after-cancel
    path (app.services.run_service.RunService._resume_cancelled)."""
    if from_status != "cancelled":
        raise RunTransitionError(
            f"cannot resume a run that is not cancelled (status={from_status!r})"
        )
