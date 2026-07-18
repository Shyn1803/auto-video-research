"""Task 4-7 Step 6 -- cancel vs node-finish race (AC2), run 20x as a
flaky-hunter per the task's Definition of Done.

This codebase's pipeline execution is single-coroutine per run (no
background-task/worker split exists yet in this Phase 1 monolith --
app/services/run_service.py's RunService._execute_node runs the node inline
and awaits it to completion before the request handler responds). That
means the "race" is resolved by construction, not by luck: the
cancel_requested_at check in _execute_node happens at exactly one point --
right after graph.ainvoke() returns, before the node's completion write --
so there is no nondeterministic window. The 20x loop below exists to prove
that determinism empirically (per the task's explicit DoD), not because the
implementation is expected to occasionally flake.
"""

from __future__ import annotations

import unittest.mock as mock
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.events import bus as bus_mod
from app.pipeline import graph as graph_mod
from app.pipeline.state import NodeName, RunStatus
from app.services.run_service import RunConflictError, RunService

REPEATS = 20


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


class FakeSession:
    def __init__(self):
        self.added: list = []
        self.flush_count = 0
        self._queue: list = []

    async def execute(self, _stmt):
        value = self._queue.pop(0) if self._queue else None
        return FakeResult(value)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def get(self, _model, pk):
        for obj in self.added:
            if getattr(obj, "id", None) == pk:
                return obj
        return None


class FakeProject:
    def __init__(self, status: str = "DRAFT"):
        self.id = uuid4()
        self.status = status


@pytest.fixture(autouse=True)
async def _drain_bus():
    await bus_mod.drain()
    yield


@pytest.mark.asyncio
async def test_cancel_arriving_mid_node_always_resolves_to_cancelled_20x():
    """Cancel requested *before* graph.ainvoke() returns -> always CANCELLED,
    never left ambiguous/half-written, across 20 independent runs."""
    for _ in range(REPEATS):
        project = FakeProject(status="DRAFT")
        session = FakeSession()
        session._queue = [None]
        svc = RunService(session, checkpointer=InMemorySaver())

        async def cancel_mid_flight(state, svc=svc, project=project, session=session):
            run = session.added[0]
            await svc.cancel_run(project, run, actor="user-2")
            return await graph_mod._stub_node(state, NodeName.RESEARCH)

        with mock.patch.dict(graph_mod.NODE_FNS, {NodeName.RESEARCH: cancel_mid_flight}):
            run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

        assert run.status == RunStatus.CANCELLED.value
        assert run.interrupted_node == NodeName.RESEARCH.value
        assert run.previous_status is not None


@pytest.mark.asyncio
async def test_cancel_arriving_after_node_already_finished_never_corrupts_state_20x():
    """Cancel requested *after* the node has already completed and its
    INTERRUPTED write landed -> the completed node's outcome is untouched;
    the run simply becomes eligible for cancellation going forward (BR-4:
    still an active status), never silently reverted/corrupted."""
    for _ in range(REPEATS):
        project = FakeProject(status="DRAFT")
        session = FakeSession()
        session._queue = [None]
        svc = RunService(session, checkpointer=InMemorySaver())

        run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")
        assert run.status == RunStatus.INTERRUPTED.value
        assert run.interrupted_node == NodeName.RESEARCH.value

        # cancel arrives strictly after -- must not rewrite the already-final
        # INTERRUPTED/NEED_REVIEW outcome of the node that just finished.
        cancelled = await svc.cancel_run(project, run, actor="user-2")
        assert cancelled.status == RunStatus.INTERRUPTED.value
        assert cancelled.interrupted_node == NodeName.RESEARCH.value
        assert project.status == "NEED_REVIEW"


@pytest.mark.asyncio
async def test_cancel_on_terminal_run_always_409_never_flaky_20x():
    """BR-4: cancelling an already-CANCELLED run is rejected every time --
    no window where a second cancel could succeed or corrupt state."""
    for _ in range(REPEATS):
        project = FakeProject(status="DRAFT")
        session = FakeSession()
        session._queue = [None]
        svc = RunService(session, checkpointer=InMemorySaver())

        async def cancel_mid_flight(state, svc=svc, project=project, session=session):
            run = session.added[0]
            await svc.cancel_run(project, run, actor="user-2")
            return await graph_mod._stub_node(state, NodeName.RESEARCH)

        with mock.patch.dict(graph_mod.NODE_FNS, {NodeName.RESEARCH: cancel_mid_flight}):
            run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")
        assert run.status == RunStatus.CANCELLED.value

        with pytest.raises(RunConflictError):
            await svc.cancel_run(project, run, actor="user-3")
