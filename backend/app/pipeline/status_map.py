"""Node <-> project-state-machine mapping (Task 4-1 Step 3).

Real node semantics (what each node actually produces) belong to 4-3..4-6.
This module only answers: "when node X starts/finishes, what project status
should the state machine (1-4) be in?" -- the minimum needed for Mode 2's
human-gate interrupt-after-every-node behaviour (AC1) to move the project
through a status a human can see and act on.

Known simplification (flagged, not hidden): ProjectStatus has exactly one
review gate (NEED_REVIEW/REVISING -> APPROVED) before production, but Mode 2
interrupts after *every* node per "Decisions already locked". Nodes between
research and storyboard therefore share the NEED_REVIEW gate (idempotent
no-op transitions after the first). PRODUCE has no dedicated "awaiting
render approval" status in the current schema, so its completion is folded
into the PRODUCING -> RENDERING edge. Revisit once 4-6/4-7 need finer state.
"""

from __future__ import annotations

from app.pipeline.state import NodeName
from app.services.state_machine_edges import (
    APPROVED,
    NEED_REVIEW,
    PRODUCING,
    READY,
    RENDERING,
    RESEARCHING,
)

NODE_ORDER: list[NodeName] = [
    NodeName.RESEARCH,
    NodeName.RANKING,
    NodeName.WRITE,
    NodeName.STORYBOARD,
    NodeName.PRODUCE,
    NodeName.RENDER,
]

# Status to move into right before a node starts executing (None = leave as-is).
NODE_ENTRY_STATUS: dict[NodeName, str | None] = {
    NodeName.RESEARCH: RESEARCHING,
    NodeName.RANKING: None,
    NodeName.WRITE: None,
    NodeName.STORYBOARD: None,
    NodeName.PRODUCE: PRODUCING,
    NodeName.RENDER: RENDERING,
}

# Status to move into once a node finishes -- this is the interrupt-point
# status a human sees while the run is paused awaiting approval (Mode 2).
NODE_COMPLETE_STATUS: dict[NodeName, str | None] = {
    NodeName.RESEARCH: NEED_REVIEW,
    NodeName.RANKING: NEED_REVIEW,
    NodeName.WRITE: NEED_REVIEW,
    NodeName.STORYBOARD: APPROVED,
    NodeName.PRODUCE: None,
    NodeName.RENDER: READY,
}


def next_node(current: NodeName) -> NodeName | None:
    """Return the node after *current*, or None if it was the last."""
    idx = NODE_ORDER.index(current)
    if idx + 1 >= len(NODE_ORDER):
        return None
    return NODE_ORDER[idx + 1]
