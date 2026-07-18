"""Task 4-7 Steps 2/3/5 -- cancel endpoint, usage/version preservation (BR-2/BR-3),
resume-after-cancel via the existing start_run path.

Same FakeSession/FakeProject pattern as tests/unit/pipeline/test_run_service.py
(no live Postgres in this sandbox) -- "mid-node cancel" is simulated by having
the monkeypatched node function itself call ``RunService.cancel_run()`` against
the *same* run object before returning, which is exactly what a concurrent
request would do to the shared DB row in production (both would resolve to the
same ``cancel_requested_at`` value once committed).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.events import bus as bus_mod
from app.models.pipeline_run import PipelineRun
from app.pipeline import graph as graph_mod
from app.pipeline.state import NodeName, RunStatus
from app.services.run_service import RunConflictError, RunService


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


class FakeSession:
    """Same shape as test_run_service.py's FakeSession -- a mutable `_queue`
    of canned `execute()` results, refillable mid-test via `session._queue =
    [...]` (used by the resume-after-cancel test to feed the second
    start_run() call's active-run + last-cancelled-run lookups)."""

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


def make_session(execute_queue=None):
    s = FakeSession()
    s._queue = list(execute_queue or [])
    return s


class FakeProject:
    def __init__(self, status: str = "DRAFT"):
        self.id = uuid4()
        self.status = status


@pytest.fixture(autouse=True)
async def _drain_bus():
    await bus_mod.drain()
    yield


@pytest.mark.asyncio
async def test_cancel_mid_node_lands_on_cancelled_after_node_finishes(monkeypatch):
    """AC1/BR-1: cancel requested while research is executing -> run finishes
    as CANCELLED (not INTERRUPTED) once the in-flight node completes, and the
    project's completion-status transition still runs (needed for Step 5
    resume to have somewhere sensible to resume into)."""
    project = FakeProject(status="DRAFT")
    session = make_session(execute_queue=[None])  # no active run check
    svc = RunService(session, checkpointer=InMemorySaver())

    events: list = []

    async def _subscribe():
        async for evt in bus_mod.subscribe("run.cancelled"):
            events.append(evt)
            break

    import asyncio

    listener = asyncio.ensure_future(_subscribe())
    await asyncio.sleep(0)  # let the subscriber attach before publish happens

    async def research_that_gets_cancelled_mid_flight(state):
        # Simulates a concurrent POST /cancel arriving while this node runs.
        run = session.added[0]  # the PipelineRun added by start_run()
        await svc.cancel_run(project, run, actor="user-2")
        return await graph_mod._stub_node(state, NodeName.RESEARCH)

    monkeypatch.setitem(
        graph_mod.NODE_FNS, NodeName.RESEARCH, research_that_gets_cancelled_mid_flight
    )

    run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    assert run.status == RunStatus.CANCELLED.value
    assert run.interrupted_node == NodeName.RESEARCH.value
    assert run.previous_status == "NEED_REVIEW"  # research's own completion bucket
    assert project.status == "NEED_REVIEW"

    await asyncio.wait_for(listener, timeout=1)
    assert len(events) == 1
    assert events[0]["payload"]["step"] == NodeName.RESEARCH.value


@pytest.mark.asyncio
async def test_cancel_after_run_already_finished_returns_conflict_ac3():
    """AC3/BR-4: cancelling a COMPLETED/FAILED/CANCELLED run -> 409-worthy."""
    project = FakeProject(status="READY")
    finished_run = PipelineRun(
        id=uuid4(), project_id=project.id, status=RunStatus.COMPLETED.value
    )
    session = make_session()
    svc = RunService(session, checkpointer=InMemorySaver())

    with pytest.raises(RunConflictError):
        await svc.cancel_run(project, finished_run, actor="user-1")


@pytest.mark.asyncio
async def test_cancel_does_not_race_when_node_already_finished_ac2():
    """AC2: if graph.ainvoke() has already returned (node genuinely done)
    before cancel_requested_at gets set, the run must finish normally at its
    interrupt point -- never retroactively become CANCELLED."""
    project = FakeProject(status="DRAFT")
    session = make_session(execute_queue=[None])
    svc = RunService(session, checkpointer=InMemorySaver())

    # No cancel call at all during node execution -- the normal path.
    run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    assert run.status == RunStatus.INTERRUPTED.value
    assert run.interrupted_node == NodeName.RESEARCH.value

    # A cancel arriving *after* the node's completion was already written is
    # still valid (run is now INTERRUPTED, an active status) but does not
    # retroactively corrupt what already happened -- it only affects the
    # *next* node's completion, exactly like the mid-flight case above.
    cancelled_run = await svc.cancel_run(project, run, actor="user-2")
    assert cancelled_run.status == RunStatus.INTERRUPTED.value  # unchanged so far
    assert cancelled_run.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_usage_and_versions_preserved_across_cancel_br2_br3():
    """BR-2/BR-3: complete_node still runs (StepVersion + usage bookkeeping)
    for the node that was in flight when cancel was requested -- cancel only
    stops *forward* progress, it is not a rollback."""
    project = FakeProject(status="DRAFT")
    session = make_session(execute_queue=[None])
    svc = RunService(session, checkpointer=InMemorySaver())

    async def cancel_mid_flight(state):
        run = session.added[0]
        await svc.cancel_run(project, run, actor="user-2")
        return await graph_mod._stub_node(state, NodeName.RESEARCH)

    import unittest.mock as mock

    with mock.patch.dict(graph_mod.NODE_FNS, {NodeName.RESEARCH: cancel_mid_flight}):
        run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    assert run.status == RunStatus.CANCELLED.value
    # complete_node's StepVersion insert went through session.add() same as
    # any normal completion -- added list holds the run AND its StepVersion.
    from app.models.step_version import StepVersion

    versions = [o for o in session.added if isinstance(o, StepVersion)]
    assert len(versions) == 1
    assert versions[0].step == "research"


@pytest.mark.asyncio
async def test_resume_after_cancel_continues_same_checkpoint_thread_ac1():
    """AC1/Step 5: starting a new run after CANCELLED reuses the cancelled
    run's own id as thread_id, so research is not re-executed."""
    project = FakeProject(status="DRAFT")
    session = make_session(execute_queue=[None])
    saver = InMemorySaver()
    svc = RunService(session, checkpointer=saver)

    calls: list[str] = []

    async def counting_research(state):
        calls.append("research")
        return await graph_mod._stub_node(state, NodeName.RESEARCH)

    async def cancel_mid_flight(state):
        run = session.added[0]
        await svc.cancel_run(project, run, actor="user-2")
        return await counting_research(state)

    import unittest.mock as mock

    with mock.patch.dict(graph_mod.NODE_FNS, {NodeName.RESEARCH: cancel_mid_flight}):
        first_run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    assert first_run.status == RunStatus.CANCELLED.value
    assert calls == ["research"]

    # `_active_run` and `_last_cancelled_run` both re-query via session.execute
    # -- feed the fake session's queue for the second start_run() call: no
    # active run, then the cancelled run found by project_id.
    session._queue = [None, first_run]

    second_run = await svc.start_run(project, NodeName.RANKING, actor="user-1")

    # Same row reused (not a brand-new PipelineRun.id) -- same LangGraph
    # thread_id, so the checkpoint continues instead of restarting.
    assert second_run.id == first_run.id
    assert second_run.interrupted_node == NodeName.RANKING.value
    assert calls == ["research"], "research must not re-execute on resume-after-cancel"
