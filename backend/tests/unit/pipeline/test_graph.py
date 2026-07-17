"""Task 4-1 Step 1/3/9 -- graph skeleton + interrupt-after-every-node (AC5)."""

from __future__ import annotations

import pytest

from app.pipeline.graph import NODE_SEQUENCE, build_graph
from app.pipeline.state import NodeName, PipelineState


def test_build_graph_compiles_without_error():
    """Step 1 verify: import + compile must not raise."""
    graph = build_graph()
    assert graph is not None


def test_interrupt_after_configured_for_all_six_nodes():
    """AC5 / Step 3: Mode 2 pauses after *every* node, including produce/render."""
    compiled = build_graph()
    interrupt_nodes = compiled.interrupt_after_nodes
    assert set(interrupt_nodes) == {n.value for n in NodeName}
    assert len(NODE_SEQUENCE) == 6


@pytest.mark.asyncio
async def test_happy_path_research_then_resume_ranking():
    """AC1 skeleton: run -> interrupt after research -> resume -> ranking runs next."""
    from langgraph.checkpoint.memory import InMemorySaver

    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "run-1"}}
    state = PipelineState(project_id="p1", run_id="run-1")

    result = await graph.ainvoke(state, config=config)
    assert result["completed_nodes"] == [NodeName.RESEARCH]

    result = await graph.ainvoke(None, config=config)
    assert result["completed_nodes"] == [NodeName.RESEARCH, NodeName.RANKING]


@pytest.mark.asyncio
async def test_resume_does_not_rerun_completed_node(monkeypatch):
    """AC2: kill mid-run, restart, resume -- a completed node must not re-execute."""
    from langgraph.checkpoint.memory import InMemorySaver

    calls: list[str] = []
    import app.pipeline.graph as graph_mod

    async def counting_research(state: PipelineState) -> dict:
        calls.append("research")
        return await graph_mod._stub_node(state, NodeName.RESEARCH)

    monkeypatch.setitem(graph_mod.NODE_FNS, NodeName.RESEARCH, counting_research)

    saver = InMemorySaver()
    graph = build_graph(saver)
    config = {"configurable": {"thread_id": "run-crash"}}
    state = PipelineState(project_id="p1", run_id="run-crash")

    await graph.ainvoke(state, config=config)
    assert calls == ["research"]

    # Simulate "process restarted": build a brand-new compiled graph from the
    # same checkpointer/thread_id and resume -- research must not run again.
    graph2 = build_graph(saver)
    await graph2.ainvoke(None, config=config)
    assert calls == ["research"], "research re-ran after resume -- checkpoint not honoured"
