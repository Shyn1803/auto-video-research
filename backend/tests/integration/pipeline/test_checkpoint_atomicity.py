"""Task 4-1 Step 8 -- fault injection: BR-3 atomicity + AC2 resume-without-rerun.

Most important test in this task per its Definition of Done.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.models.pipeline_run import PipelineRun
from app.pipeline import graph as graph_mod
from app.pipeline.nodes.base import complete_node
from app.pipeline.state import NodeName


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class CrashAfterFirstAddSession:
    """Simulates "process killed after writing one of the two rows" (BR-3).

    Raises once ``add()`` has been called once (StepVersion staged) but
    before the second add()/flush() -- an all-or-nothing session.begin()
    equivalent: nothing committed means neither write survives.
    """

    def __init__(self, crash_after_n_adds: int):
        self.added: list = []
        self._crash_after = crash_after_n_adds
        self.flush_calls = 0

    async def execute(self, _stmt):
        return FakeResult(None)  # no prior step_versions -> version 1

    def add(self, obj):
        self.added.append(obj)
        if len(self.added) >= self._crash_after:
            raise RuntimeError("simulated process kill mid-write")

    async def flush(self):
        self.flush_calls += 1


@pytest.mark.asyncio
async def test_crash_between_step_version_and_run_write_leaves_neither_persisted():
    """BR-3: if the process dies after the StepVersion add() but before the
    PipelineRun update is staged, flush() must never have been reached --
    an "all or nothing" outcome (in real Postgres this is the transaction
    rolling back; here it's the flush() that would COMMIT the two writes
    together never being called at all)."""
    project_id = uuid4()
    run = PipelineRun(id=uuid4(), project_id=project_id, status="running")

    # crash_after_n_adds=1 -> raises right after the StepVersion is staged,
    # before the PipelineRun mutation/add that would normally follow.
    session = CrashAfterFirstAddSession(crash_after_n_adds=1)

    with pytest.raises(RuntimeError, match="simulated process kill"):
        await complete_node(
            session,
            project_id=project_id,
            node=NodeName.RESEARCH,
            content={"foo": "bar"},
            actor="user-1",
            run=run,
            run_updates={"status": "interrupted", "interrupted_node": "research"},
        )

    # flush() (the point at which both writes would become durable) was
    # never reached -- neither write "took" from the caller's perspective.
    assert session.flush_calls == 0
    # The run object itself was never mutated either (run_updates loop
    # comes after the StepVersion add() in complete_node/record_step_and_run).
    assert run.status == "running"
    assert run.interrupted_node is None


@pytest.mark.asyncio
async def test_resume_after_crash_does_not_rerun_completed_research_node(monkeypatch):
    """AC2: kill process mid-run (after research completes), restart,
    resume -- research must not execute a second time."""
    from app.pipeline.state import PipelineState

    calls: list[str] = []

    async def counting_research(state):
        calls.append("research")
        return await graph_mod._stub_node(state, NodeName.RESEARCH)

    monkeypatch.setitem(graph_mod.NODE_FNS, NodeName.RESEARCH, counting_research)

    saver = InMemorySaver()
    run_id = str(uuid4())
    config = {"configurable": {"thread_id": run_id}}

    # "process A": runs research, then dies (simulated by just not continuing).
    graph_a = graph_mod.build_graph(saver)
    state = PipelineState(project_id="p1", run_id=run_id)
    result = await graph_a.ainvoke(state, config=config)
    assert result["completed_nodes"] == [NodeName.RESEARCH]
    assert calls == ["research"]

    # "process B": brand-new compiled graph (simulating app restart), same
    # checkpointer + thread_id -- resuming must continue at ranking, not
    # re-run research.
    graph_b = graph_mod.build_graph(saver)
    result2 = await graph_b.ainvoke(None, config=config)
    assert result2["completed_nodes"] == [NodeName.RESEARCH, NodeName.RANKING]
    assert calls == ["research"], "research re-executed on resume after crash"
