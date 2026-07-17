"""StepVersion writes -- Task 4-1 BR-3: atomic with the run's checkpoint row.

Per BR-3 ("Node hoàn thành → checkpoint + step_version ghi cùng transaction"),
a completed node's content snapshot (StepVersion) and its run bookkeeping
(PipelineRun.current_node/status/retry_count) must never be observed out of
sync. Both writes are staged on the same SQLAlchemy session and flushed
together here; the caller commits once (same pattern as ProjectService --
services stage, the request/orchestration layer commits, see
app/api/projects.py).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.models.pipeline_run import PipelineRun
from app.models.step_version import StepVersion


async def _next_version(session: Any, project_id: Any, step: str) -> int:
    result = await session.execute(
        select(func.max(StepVersion.version)).where(
            StepVersion.project_id == project_id, StepVersion.step == step
        )
    )
    current_max = result.scalar()
    return (current_max or 0) + 1


async def record_step_and_run(
    session: Any,
    *,
    project_id: Any,
    step: str,
    content: dict,
    created_by: str,
    run: PipelineRun,
    run_updates: dict[str, Any],
) -> StepVersion:
    """Insert a new StepVersion row and apply *run_updates* to *run*.

    Both mutations are flushed as one unit -- if the process dies between
    "content written" and "run bookkeeping written" the whole flush/commit
    rolls back atomically (BR-3). Never call this in two separate
    session.flush()/commit() calls for the two halves.
    """
    version = await _next_version(session, project_id, step)
    step_version = StepVersion(
        project_id=project_id,
        step=step,
        version=version,
        content=content,
        created_by=created_by,
    )
    session.add(step_version)

    for key, value in run_updates.items():
        setattr(run, key, value)
    session.add(run)

    await session.flush()
    return step_version
