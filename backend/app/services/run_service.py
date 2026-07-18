"""RunService -- Task 4-1 Steps 5-7: run/approve/get-run + retry->FAILED + SSE.

Owns the only code path that starts/advances/approves a pipeline run so
BR-1/BR-2/BR-4 are enforced in exactly one place (rules/code-style.md: no
business logic in routers).

Resume model: ``graph.ainvoke(None, config)`` with ``thread_id=run_id`` is
how LangGraph resumes a paused/crashed run from its last checkpoint (AC2) --
this service never re-derives node state itself, it always asks the
compiled graph to continue.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.events.bus import publish
from app.events.schemas import run_cancelled, step_progress
from app.models.pipeline_run import ACTIVE_RUN_STATUSES, PipelineRun
from app.pipeline.graph import build_graph
from app.pipeline.nodes.base import complete_node
from app.pipeline.state import NodeName, PipelineState, RunStatus
from app.pipeline.status_map import (
    NODE_COMPLETE_STATUS,
    NODE_ENTRY_STATUS,
    next_node,
)
from app.services.run_state_machine import RunTransitionError, validate_cancel_edge
from app.services.state_machine import ProjectStateMachine

logger = logging.getLogger(__name__)


class RunConflictError(Exception):
    """Raised for BR-1 (already-active run) / BR-2 (approve wrong node) /
    BR-4 (cancel on a non-active run, Task 4-7)."""


class RunService:
    def __init__(
        self,
        session: Any,
        checkpointer: Any = None,
        state_machine: ProjectStateMachine | None = None,
    ) -> None:
        self._session = session
        self._checkpointer = checkpointer
        self._state_machine = state_machine or ProjectStateMachine()

    async def get_active_run(self, project_id: Any) -> PipelineRun | None:
        """Public accessor -- routers use this to find the run to approve."""
        return await self._active_run(project_id)

    async def _active_run(self, project_id: Any) -> PipelineRun | None:
        result = await self._session.execute(
            select(PipelineRun).where(
                PipelineRun.project_id == project_id,
                PipelineRun.status.in_(ACTIVE_RUN_STATUSES),
            )
        )
        return result.scalar_one_or_none()

    async def _last_cancelled_run(self, project_id: Any) -> PipelineRun | None:
        """Task 4-7 Step 5 -- most recent CANCELLED run for a project, if any."""
        result = await self._session.execute(
            select(PipelineRun)
            .where(
                PipelineRun.project_id == project_id,
                PipelineRun.status == RunStatus.CANCELLED.value,
            )
            .order_by(PipelineRun.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def start_run(self, project: Any, step: NodeName, actor: str) -> PipelineRun:
        """POST /projects/{id}/steps/{step}/run -- BR-1.

        Task 4-7 Step 5: if the project's *last* run was CANCELLED (not
        just any terminal run -- FAILED resume is a separate, not-yet-built
        feature per pipeline_run.py's own comment), starting a new run
        continues that run's LangGraph checkpoint instead of opening an
        unrelated thread with no history. LangGraph's checkpoint is keyed
        by ``thread_id = str(PipelineRun.id)`` (app/pipeline/checkpoint.py),
        so a brand-new PipelineRun row would silently re-run every
        already-completed node from scratch -- reusing the cancelled run's
        id is what makes "resume sau cancel = run mới từ checkpoint" true
        rather than just a plausible-sounding new-run-that-starts-over.
        """
        existing = await self._active_run(project.id)
        if existing is not None:
            raise RunConflictError(
                f"project {project.id} already has an active run {existing.id}"
            )

        cancelled = await self._last_cancelled_run(project.id)
        if cancelled is not None:
            return await self._resume_cancelled(project, cancelled, step, actor)

        run = PipelineRun(
            id=uuid4(),
            project_id=project.id,
            status=RunStatus.RUNNING.value,
            current_node=step.value,
            retry_count=0,
        )
        self._session.add(run)
        await self._session.flush()

        await self._execute_node(project, run, step, actor, resume=False)
        return run

    async def _resume_cancelled(
        self, project: Any, run: PipelineRun, step: NodeName, actor: str
    ) -> PipelineRun:
        """Task 4-7 Step 5 -- reopen a CANCELLED run's own row/thread_id."""
        run.status = RunStatus.RUNNING.value
        run.current_node = step.value
        run.interrupted_node = None
        run.cancel_requested_at = None
        self._session.add(run)
        await self._session.flush()

        await self._execute_node(project, run, step, actor, resume=True)
        return run

    async def cancel_run(self, project: Any, run: PipelineRun, actor: str) -> PipelineRun:
        """POST /projects/{id}/runs/{run_id}/cancel -- Task 4-7 BR-1/BR-4.

        Best-effort: records the request immediately (BR-4 -- 409 if the
        run is already terminal) but does NOT flip status to CANCELLED
        here. The in-flight node (if any) is left to finish -- "kết thúc
        sau LLM call hiện tại" -- and _execute_node checks
        ``cancel_requested_at`` right after ``graph.ainvoke()`` returns,
        before writing the node's completion transition, to decide whether
        this run lands on CANCELLED or its normal INTERRUPTED/COMPLETED
        outcome (AC2: a cancel that arrives after the node has already
        finished must never retroactively corrupt that finish).
        """
        try:
            validate_cancel_edge(run.status)
        except RunTransitionError as exc:
            raise RunConflictError(str(exc)) from exc

        run.cancel_requested_at = datetime.now(UTC)
        self._session.add(run)
        await self._session.flush()
        return run

    async def approve(
        self, project: Any, run: PipelineRun, step: NodeName, actor: str
    ) -> PipelineRun:
        """POST /projects/{id}/steps/{step}/approve -- BR-2."""
        if (
            run.status != RunStatus.INTERRUPTED.value
            or run.interrupted_node != step.value
        ):
            raise RunConflictError(
                f"run {run.id} is not interrupted at {step.value} "
                f"(status={run.status}, interrupted_node={run.interrupted_node})"
            )

        nxt = next_node(step)
        if nxt is None:
            run.status = RunStatus.COMPLETED.value
            run.current_node = None
            run.interrupted_node = None
            self._session.add(run)
            await self._session.flush()
            return run

        await self._execute_node(project, run, nxt, actor, resume=True)
        return run

    async def get_run(self, run_id: Any) -> PipelineRun | None:
        return await self._session.get(PipelineRun, run_id)

    async def _execute_node(
        self,
        project: Any,
        run: PipelineRun,
        node: NodeName,
        actor: str,
        *,
        resume: bool,
    ) -> None:
        run_id = str(run.id)
        correlation_id = run_id

        entry_status = NODE_ENTRY_STATUS.get(node)
        if entry_status is not None:
            await self._state_machine.transition(
                project, entry_status, actor=actor, session=self._session
            )

        await self._publish_progress(project.id, run_id, node, pct=0, message="started")

        graph = build_graph(self._checkpointer)
        config = {"configurable": {"thread_id": run_id}}
        initial = (
            None
            if resume
            else PipelineState(
                project_id=str(project.id),
                run_id=run_id,
                current_node=node,
                status=RunStatus.RUNNING,
            )
        )

        try:
            result = await graph.ainvoke(initial, config=config)
        except Exception as exc:  # noqa: BLE001 -- BR-4: retries exhausted -> FAILED
            logger.error(
                "node %s failed after retries run=%s: %s",
                node.value,
                run_id,
                exc,
                extra={"correlation_id": correlation_id},
            )
            previous_status = project.status
            run.status = RunStatus.FAILED.value
            run.error = str(exc)
            run.previous_status = previous_status
            run.retry_count = (run.retry_count or 0) + 1
            self._session.add(run)
            await self._session.flush()
            await self._state_machine.transition(
                project,
                "FAILED",
                actor="system",
                reason=f"node {node.value} failed: {exc}",
                session=self._session,
            )
            return

        content = result.get(node.value, {}) if isinstance(result, dict) else {}

        complete_status = NODE_COMPLETE_STATUS.get(node)
        if complete_status is not None:
            await self._state_machine.transition(
                project, complete_status, actor=actor, session=self._session
            )

        # Task 4-7 BR-1/AC2: the cancel check happens here -- right after the
        # node's ainvoke() call returns, before this node's own completion is
        # written -- so the outcome is deterministic: a cancel recorded
        # before this line lands on CANCELLED; a cancel that arrives after
        # (i.e. after we already read cancel_requested_at as unset) can no
        # longer affect this write, so the run finishes normally at its
        # interrupt point instead (no corrupted/ambiguous state, AC2).
        if run.cancel_requested_at is not None:
            run_updates = {
                "status": RunStatus.CANCELLED.value,
                "current_node": None,
                "interrupted_node": node.value,
                "previous_status": project.status,
            }
            await complete_node(
                self._session,
                project_id=project.id,
                node=node,
                content=content,
                actor=actor,
                run=run,
                run_updates=run_updates,
            )
            await self._emit_cancelled(project.id, run_id, node)
            return

        run_updates = {
            "status": RunStatus.INTERRUPTED.value,
            "current_node": None,
            "interrupted_node": node.value,
        }
        await complete_node(
            self._session,
            project_id=project.id,
            node=node,
            content=content,
            actor=actor,
            run=run,
            run_updates=run_updates,
        )

        await self._publish_progress(project.id, run_id, node, pct=100, message="completed")

    async def _emit_cancelled(self, project_id: Any, run_id: str, node: NodeName) -> None:
        try:
            await publish(
                "run.cancelled",
                run_cancelled(
                    project_id=str(project_id),
                    run_id=run_id,
                    step=node.value,
                    correlation_id=run_id,
                ).model_dump(),
            )
        except Exception:  # noqa: BLE001 -- event bus is fire-and-forget
            logger.debug("event bus unavailable for run.cancelled run=%s", run_id)

    async def _publish_progress(
        self, project_id: Any, run_id: str, node: NodeName, *, pct: int, message: str
    ) -> None:
        try:
            await publish(
                "step.progress",
                step_progress(
                    project_id=str(project_id),
                    run_id=run_id,
                    step=node.value,
                    pct=pct,
                    correlation_id=run_id,
                    message=message,
                ).model_dump(),
            )
        except Exception:  # noqa: BLE001 -- event bus is fire-and-forget
            logger.debug("event bus unavailable for step.progress run=%s", run_id)
