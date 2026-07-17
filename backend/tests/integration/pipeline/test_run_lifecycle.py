"""Task 4-1 Step 9 -- full run lifecycle across all 6 nodes + AC coverage.

Exercises RunService end-to-end (start -> approve x5 -> completed) against
a real compiled graph (InMemorySaver checkpointer) to prove the whole chain
holds together, not just individual nodes.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

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
    def __init__(self):
        self.added: list = []
        self.flush_count = 0

    async def execute(self, _stmt):
        # active-run check always "no active run"; step-version version
        # lookups always "no prior version" -- fine, this test doesn't
        # assert on version numbers.
        return FakeResult(None)

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
    def __init__(self):
        self.id = uuid4()
        self.status = "DRAFT"


@pytest.mark.asyncio
async def test_full_lifecycle_research_to_render_completes_run():
    """AC1 (extended): walk every node via run + 5x approve to COMPLETED,
    checking the project status lands where status_map.py says it should
    at each interrupt point."""
    project = FakeProject()
    session = FakeSession()
    svc = RunService(session, checkpointer=InMemorySaver())

    run = await svc.start_run(project, NodeName.RESEARCH, actor="u1")
    assert run.interrupted_node == NodeName.RESEARCH.value
    assert project.status == "NEED_REVIEW"

    run = await svc.approve(project, run, NodeName.RESEARCH, actor="u1")
    assert run.interrupted_node == NodeName.RANKING.value
    assert project.status == "NEED_REVIEW"  # ranking has no dedicated bucket

    run = await svc.approve(project, run, NodeName.RANKING, actor="u1")
    assert run.interrupted_node == NodeName.WRITE.value
    assert project.status == "NEED_REVIEW"

    run = await svc.approve(project, run, NodeName.WRITE, actor="u1")
    assert run.interrupted_node == NodeName.STORYBOARD.value
    assert project.status == "APPROVED"  # storyboard's completion is the final review gate

    run = await svc.approve(project, run, NodeName.STORYBOARD, actor="u1")
    assert run.interrupted_node == NodeName.PRODUCE.value
    # entry-status for PRODUCE (APPROVED->PRODUCING) applies; PRODUCE's own
    # completion has no dedicated bucket, so it stays PRODUCING.
    assert project.status == "PRODUCING"

    run = await svc.approve(project, run, NodeName.PRODUCE, actor="u1")
    assert run.interrupted_node == NodeName.RENDER.value
    # entry PRODUCING->RENDERING then immediately complete RENDERING->READY
    # (both happen within the same node execution -- render is the last node).
    assert project.status == "READY"

    run = await svc.approve(project, run, NodeName.RENDER, actor="u1")
    assert run.status == RunStatus.COMPLETED.value
    assert project.status == "READY"


@pytest.mark.asyncio
async def test_br1_and_br2_enforced_together_in_one_lifecycle():
    project = FakeProject()
    session = FakeSession()
    svc = RunService(session, checkpointer=InMemorySaver())

    run = await svc.start_run(project, NodeName.RESEARCH, actor="u1")

    # BR-2: approving the wrong node (run is interrupted at RESEARCH) -> 409-worthy
    with pytest.raises(RunConflictError):
        await svc.approve(project, run, NodeName.STORYBOARD, actor="u1")

    # correct approve still works after the rejected attempt
    run = await svc.approve(project, run, NodeName.RESEARCH, actor="u1")
    assert run.interrupted_node == NodeName.RANKING.value
