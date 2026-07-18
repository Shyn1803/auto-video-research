"""Task 4-7 Step 1 -- PipelineRun.status transition matrix.

See app/services/run_state_machine.py's module docstring for why this is a
separate matrix from ProjectStateMachine's (projects.status has no
RUNNING/CANCELLED value; those live on PipelineRun.status instead).
"""

from __future__ import annotations

import pytest

from app.services.run_state_machine import (
    RunTransitionError,
    validate_cancel_edge,
    validate_resume_edge,
)


@pytest.mark.parametrize("active_status", ["pending", "running", "interrupted"])
def test_cancel_edge_valid_from_every_active_status(active_status):
    validate_cancel_edge(active_status)  # must not raise


@pytest.mark.parametrize(
    "terminal_status", ["completed", "failed", "cancelled"]
)
def test_cancel_edge_rejected_from_terminal_status(terminal_status):
    with pytest.raises(RunTransitionError):
        validate_cancel_edge(terminal_status)


def test_resume_edge_valid_only_from_cancelled():
    validate_resume_edge("cancelled")  # must not raise

    for other in ("pending", "running", "interrupted", "completed", "failed"):
        with pytest.raises(RunTransitionError):
            validate_resume_edge(other)
