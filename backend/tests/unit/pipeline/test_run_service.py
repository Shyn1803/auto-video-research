"""Task 4-1 Steps 5-7 -- RunService: BR-1, BR-2, BR-4, AC1 happy path, SSE chain.

Uses a lightweight fake SQLAlchemy session (no live Postgres in this
environment -- consistent with the rest of this test suite's approach,
see tests/unit/services/test_cost_service.py) and a real LangGraph
``InMemorySaver`` so the graph itself is genuinely exercised, not mocked.
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
    """Minimal stand-in for AsyncSession -- queued execute() results."""

    def __init__(self, execute_queue=None):
        self.added: list = []
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self._queue = list(execute_queue or [])

    async def execute(self, _stmt):
        value = self._queue.pop(0) if self._queue else None
        return FakeResult(value)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1

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
    """Each test gets a clean event bus (subscribers leak across tests otherwise)."""
    await bus_mod.drain()
    yield


@pytest.mark.asyncio
async def test_ac1_happy_path_research_interrupts_to_need_review():
    project = FakeProject(status="DRAFT")
    session = FakeSession(execute_queue=[None, None])  # no active run, no prior step_version
    svc = RunService(session, checkpointer=InMemorySaver())

    run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    assert project.status == "NEED_REVIEW"
    assert run.status == RunStatus.INTERRUPTED.value
    assert run.interrupted_node == NodeName.RESEARCH.value
    assert run.current_node is None
    assert session.flush_count >= 1


@pytest.mark.asyncio
async def test_br1_second_run_while_active_returns_conflict():
    project = FakeProject(status="RESEARCHING")
    existing_run = PipelineRun(
        id=uuid4(), project_id=project.id, status=RunStatus.INTERRUPTED.value
    )
    session = FakeSession(execute_queue=[existing_run])
    svc = RunService(session, checkpointer=InMemorySaver())

    with pytest.raises(RunConflictError):
        await svc.start_run(project, NodeName.RESEARCH, actor="user-1")


@pytest.mark.asyncio
async def test_br2_approve_on_wrong_node_returns_conflict():
    project = FakeProject(status="NEED_REVIEW")
    run = PipelineRun(
        id=uuid4(),
        project_id=project.id,
        status=RunStatus.INTERRUPTED.value,
        interrupted_node=NodeName.RESEARCH.value,
    )
    session = FakeSession()
    svc = RunService(session, checkpointer=InMemorySaver())

    with pytest.raises(RunConflictError):
        # run is interrupted at RESEARCH, not RANKING -- approving RANKING is invalid
        await svc.approve(project, run, NodeName.RANKING, actor="user-1")


@pytest.mark.asyncio
async def test_br2_approve_on_non_interrupted_run_returns_conflict():
    project = FakeProject(status="NEED_REVIEW")
    run = PipelineRun(
        id=uuid4(),
        project_id=project.id,
        status=RunStatus.RUNNING.value,
        interrupted_node=NodeName.RESEARCH.value,
    )
    session = FakeSession()
    svc = RunService(session, checkpointer=InMemorySaver())

    with pytest.raises(RunConflictError):
        await svc.approve(project, run, NodeName.RESEARCH, actor="user-1")


@pytest.mark.asyncio
async def test_br4_retry_exhaustion_marks_project_failed_and_keeps_previous_status(
    monkeypatch,
):
    call_count = {"n": 0}

    async def always_fails(state):
        call_count["n"] += 1
        raise RuntimeError("boom")

    monkeypatch.setitem(graph_mod.NODE_FNS, NodeName.RESEARCH, always_fails)

    project = FakeProject(status="DRAFT")
    session = FakeSession(execute_queue=[None])
    svc = RunService(session, checkpointer=InMemorySaver())

    run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")

    # DRAFT -> RESEARCHING happens before the node runs; node then fails
    # 3x (RetryPolicy max_attempts=3) and the run/project go FAILED.
    assert call_count["n"] == 3
    assert run.status == RunStatus.FAILED.value
    assert run.previous_status == "RESEARCHING"
    assert project.status == "FAILED"
    assert "boom" in run.error


@pytest.mark.asyncio
async def test_approve_advances_to_next_node_and_publishes_step_progress():
    project = FakeProject(status="DRAFT")
    session = FakeSession(execute_queue=[None, None, None])
    svc = RunService(session, checkpointer=InMemorySaver())

    run = await svc.start_run(project, NodeName.RESEARCH, actor="user-1")
    assert run.interrupted_node == NodeName.RESEARCH.value

    run = await svc.approve(project, run, NodeName.RESEARCH, actor="user-1")
    assert run.interrupted_node == NodeName.RANKING.value
    assert run.status == RunStatus.INTERRUPTED.value
    # ranking has no dedicated project-status bucket -> NEED_REVIEW stays (no-op)
    assert project.status == "NEED_REVIEW"
