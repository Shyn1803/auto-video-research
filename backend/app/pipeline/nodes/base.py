"""Shared node-completion plumbing (Task 4-1 Steps 4 & 6).

Real per-node business logic lives in app/pipeline/nodes/{node}.py from
4-3 onward -- this module only provides the two things every node needs
regardless of its content:

1. ``NODE_TO_STEP_VERSION_KEY`` -- which ``step_versions.step`` bucket a
   node's output belongs to (see StepVersion's existing CHECK constraint,
   app/models/step_version.py). RANKING has no dedicated bucket yet: it's
   folded into the research review as a sub-activity (fact-check runs
   against the research package, no separate artifact type exists in the
   schema today) -- 4-4 may revisit this if fact-check needs its own
   versioned content. WRITE is mapped to "script" (its terminal artifact);
   4-3/4-5 may want research to write "outline" fully separately -- flagged
   for those tasks, not resolved here (Scope Out: real node logic).
2. ``complete_node`` -- the one place that writes a node's StepVersion and
   PipelineRun bookkeeping atomically (BR-3) and logs with correlation_id
   (rules/logging.md) set to the run id.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.pipeline_run import PipelineRun
from app.pipeline.state import NodeName
from app.services.step_version import record_step_and_run

logger = logging.getLogger(__name__)

NODE_TO_STEP_VERSION_KEY: dict[NodeName, str | None] = {
    NodeName.RESEARCH: "research",
    NodeName.RANKING: None,
    NodeName.WRITE: "script",
    NodeName.STORYBOARD: "storyboard",
    NodeName.PRODUCE: "produce",
    NodeName.RENDER: "render",
}


async def complete_node(
    session: Any,
    *,
    project_id: Any,
    node: NodeName,
    content: dict,
    actor: str,
    run: PipelineRun,
    run_updates: dict[str, Any],
) -> None:
    """Persist a node's output + run bookkeeping in one transaction (BR-3).

    Skips the StepVersion insert for nodes with no dedicated bucket
    (see NODE_TO_STEP_VERSION_KEY) but still applies run_updates so the
    caller only needs one code path regardless of node.
    """
    step_key = NODE_TO_STEP_VERSION_KEY.get(node)
    if step_key is not None:
        await record_step_and_run(
            session,
            project_id=project_id,
            step=step_key,
            content=content,
            created_by=actor,
            run=run,
            run_updates=run_updates,
        )
    else:
        for key, value in run_updates.items():
            setattr(run, key, value)
        session.add(run)
        await session.flush()

    logger.info(
        "node complete node=%s run=%s project=%s",
        node.value,
        run.id,
        project_id,
        extra={"correlation_id": str(run.id)},
    )
