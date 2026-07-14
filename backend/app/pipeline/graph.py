"""Pipeline graph — LangGraph skeleton for the 6-node AVR pipeline.

This module is intentionally a thin orchestrator: it wires node stubs
and exposes the compile/execute entrypoints.
Real node logic lives in app/pipeline/nodes/{node_name}.py (Epic 4 tasks).

LangGraph is not yet installed. Stubs below keep the interface stable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from app.pipeline.state import NodeName, PipelineState, RunStatus

logger = logging.getLogger(__name__)

NodeFn = Callable[[PipelineState], Coroutine[Any, Any, PipelineState]]


async def _stub_node(state: PipelineState, name: NodeName) -> PipelineState:
    """Pass-through stub — marks the node complete without transforming."""
    logger.info("pipeline node stub: %s run=%s", name, state.run_id)
    state.current_node = name
    state.completed_nodes.append(name)
    state.current_node = None
    return state


async def research_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.RESEARCH)


async def ranking_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.RANKING)


async def write_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.WRITE)


async def storyboard_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.STORYBOARD)


async def produce_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.PRODUCE)


async def render_node(state: PipelineState) -> PipelineState:
    return await _stub_node(state, NodeName.RENDER)


NODE_SEQUENCE: list[tuple[NodeName, NodeFn]] = [
    (NodeName.RESEARCH, research_node),
    (NodeName.RANKING, ranking_node),
    (NodeName.WRITE, write_node),
    (NodeName.STORYBOARD, storyboard_node),
    (NodeName.PRODUCE, produce_node),
    (NodeName.RENDER, render_node),
]


async def run_pipeline(state: PipelineState) -> PipelineState:
    """Execute all 6 nodes sequentially. Returns final state."""
    state.status = RunStatus.RUNNING
    for node_name, node_fn in NODE_SEQUENCE:
        state.current_node = node_name
        state = await node_fn(state)
    state.status = RunStatus.COMPLETED
    state.current_node = None
    logger.info("pipeline complete: run=%s nodes=%s", state.run_id, state.completed_nodes)
    return state


def build_graph() -> None:
    """Placeholder: returns without error to satisfy Step 1 verify."""
    logger.info("build_graph stub (LangGraph not yet installed)")
    return None
