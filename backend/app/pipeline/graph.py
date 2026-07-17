"""Pipeline graph -- LangGraph wiring for the 6-node AVR pipeline (Task 4-1).

This module is intentionally a thin orchestrator: it wires node stubs and
exposes the compile entrypoint. Real node logic lives in
app/pipeline/nodes/{node_name}.py (Epic 4 tasks 4-3..4-6) -- per Scope Out,
produce/render stay no-op stubs here regardless.

Per "Decisions already locked": Mode 2 interrupts after *every* node,
including produce/render -- ``interrupt_after`` below lists all six.
Retry-with-backoff (BR-4) uses LangGraph's own ``RetryPolicy`` rather than
reinventing one (rules/error-handling.md: nodes must be safely re-entrant
anyway, since a crash resumes at the checkpoint).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.pipeline.state import NodeName, PipelineState

logger = logging.getLogger(__name__)

NodeFn = Callable[[PipelineState], Coroutine[Any, Any, dict[str, Any]]]

# 3 attempts total per BR-4 ("Retry hết 3 lần"); short/deterministic backoff
# so unit tests stay fast (real HTTP-backed nodes will tune this per-adapter
# once 4-3+ lands).
RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.05,
    backoff_factor=2.0,
    jitter=False,
    # LangGraph's default retry_on skips several common exception types
    # (ValueError, RuntimeError, ...) -- too narrow here, since node
    # failures should retry regardless of exception shape until adapters
    # (4-3+) start raising typed ProviderError(retryable=...) per
    # rules/error-handling.md, at which point this can narrow again.
    retry_on=lambda _exc: True,
)


async def _stub_node(state: PipelineState, name: NodeName) -> dict[str, Any]:
    """Pass-through stub -- marks the node complete without transforming state.

    Returns a partial-state dict (LangGraph merges it into PipelineState),
    not a mutated copy of *state* -- nodes must stay side-effect-free on
    their input per the checkpoint/resume contract.
    """
    logger.info("pipeline node stub: %s run=%s", name.value, state.run_id)
    return {
        "current_node": None,
        "completed_nodes": [*state.completed_nodes, name],
    }


async def research_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.RESEARCH)


async def ranking_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.RANKING)


async def write_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.WRITE)


async def storyboard_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.STORYBOARD)


async def produce_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.PRODUCE)


async def render_node(state: PipelineState) -> dict[str, Any]:
    return await _stub_node(state, NodeName.RENDER)


NODE_FNS: dict[NodeName, NodeFn] = {
    NodeName.RESEARCH: research_node,
    NodeName.RANKING: ranking_node,
    NodeName.WRITE: write_node,
    NodeName.STORYBOARD: storyboard_node,
    NodeName.PRODUCE: produce_node,
    NodeName.RENDER: render_node,
}

NODE_SEQUENCE: list[NodeName] = list(NODE_FNS)


def build_graph(checkpointer: Any = None) -> Any:
    """Compile the 6-node pipeline graph.

    *checkpointer* is any LangGraph ``BaseCheckpointSaver`` (Postgres in
    production via app/pipeline/checkpoint.py, ``InMemorySaver`` in tests).
    Omitting it still compiles (used by the Step-1 smoke check) but disables
    real interrupt/resume persistence.
    """
    graph: StateGraph = StateGraph(PipelineState)

    for name, fn in NODE_FNS.items():
        graph.add_node(name.value, fn, retry_policy=RETRY_POLICY)

    graph.add_edge(START, NODE_SEQUENCE[0].value)
    for a, b in zip(NODE_SEQUENCE, NODE_SEQUENCE[1:], strict=False):
        graph.add_edge(a.value, b.value)
    graph.add_edge(NODE_SEQUENCE[-1].value, END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_after=[n.value for n in NODE_SEQUENCE],
    )
