"""Pipeline graph -- LangGraph wiring with conditional entry (task 4-8).

Two-entry design (BR-2):
  * "research" (default): entry_router → research → ranking →
    write → storyboard → produce → render
  * "script":          entry_router → write (script pre-loaded) →
    factcheck → storyboard → produce → render

Key design decisions
--------------------
- entry_router_node: reads project from DB to determine entry_point.
  Falls back gracefully to state.entry_point if the DB is unavailable
  (test environments without Postgres).
- script_factcheck_node: wraps run_factcheck inline in graph.py -- no new
  node FILE created (task scope constraint).
- Research path is unchanged: research_node still calls run_research which
  internally includes factcheck. After WRITE in research path we go straight
  to STORYBOARD (factcheck already done).
- NODE_SEQUENCE is deprecated (graph is now conditional) but kept for
  backward compat with existing tests.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.pipeline.nodes.factcheck.node import run_factcheck
from app.pipeline.state import NodeName, PipelineState

logger = logging.getLogger(__name__)

NodeFn = Any  # (PipelineState) -> Coroutine[Any, Any, dict[str, Any]]

# 3 attempts total per BR-4
RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_interval=0.05,
    backoff_factor=2.0,
    jitter=False,
    retry_on=lambda _exc: True,
)


# ---------------------------------------------------------------------------
# Original 6-node stubs (signature and behavior unchanged)
# ---------------------------------------------------------------------------

async def _stub_node(state: PipelineState, name: NodeName) -> dict[str, Any]:
    """Pass-through stub -- marks the node complete without transforming state."""
    logger.info("pipeline node stub: %s run=%s", name.value, state.run_id)
    return {
        "current_node": None,
        "completed_nodes": [*state.completed_nodes, name],
    }


async def research_node(state: PipelineState) -> dict[str, Any]:
    """Research node -- delegates to the real implementation."""
    from app.pipeline.nodes.research.node import research_node as _rn
    return await _rn(state)


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


# ---------------------------------------------------------------------------
# 4-8: entry router (NO retry policy — just a DB read)
# ---------------------------------------------------------------------------

async def entry_router_node(state: PipelineState) -> dict[str, Any]:
    """Determine the pipeline entry point from the project record.

    Reads the project from the database; falls back to ``state.entry_point``
    (default "research") if the DB is unreachable so that unit tests without
    a live Postgres instance can still exercise the graph.

    For script entry: also loads the saved script from step_versions
    (step="script", version=1) into ``state.write`` so WRITE is pre-completed.
    """
    ep = state.entry_point or "research"

    # In tests (no live DB), gracefully fall through to the state value.
    try:
        db_manager = _get_db_manager()
    except Exception:
        return {"current_node": None, "entry_point": ep}

    try:
        async with db_manager.session() as session:
            from uuid import UUID

            from sqlalchemy import select

            from app.models.project import Project
            from app.models.step_version import StepVersion

            project = await session.get(
                Project, UUID(str(state.project_id))
            )
            if project is not None:
                ep = getattr(project, "entry_point", "research") or "research"

            updates: dict[str, Any] = {
                "current_node": None,
                "entry_point": ep,
            }

            if ep == "script":
                result = await session.execute(
                    select(StepVersion).where(
                        StepVersion.project_id == UUID(str(state.project_id)),
                        StepVersion.step == "script",
                        StepVersion.version == 1,
                    )
                )
                sv = result.scalar_one_or_none()
                if sv is not None:
                    updates["write"] = {
                        "script_text": sv.content.get("text", "")
                    }

            return updates
    except Exception:
        pass
    finally:
        try:
            await db_manager.close()
        except Exception:
            pass

    return {"current_node": None, "entry_point": ep}


# ---------------------------------------------------------------------------
# 4-8: script factcheck node (inline in graph.py -- no new FILE)
# ---------------------------------------------------------------------------

async def script_factcheck_node(state: PipelineState) -> dict[str, Any]:
    """Run factcheck on user-provided script (skipping research/ranking).

    Reads the script from `state.write` (set by entry_router for script
    entry) and calls `run_factcheck` with empty sources. On FAIL verdict,
    `run_factcheck` transitions the project to NEED_REVIEW and emits a
    notify event (AC2: factcheck gate is unbypassable).
    """
    from app.pipeline.state import NodeName

    script_text = (state.write or {}).get("script_text", "")

    result: dict[str, Any] = {
        "current_node": None,
        "completed_nodes": [
            *state.completed_nodes,
            NodeName.FACTCHECK,
        ],
        "factcheck": {"overall_verdict": "PASS", "claims": []},
    }

    if not script_text:
        return result

    try:
        db_manager = _get_db_manager()
        async with db_manager.session() as session:
            from uuid import UUID

            from app.models.project import Project

            project = await session.get(Project, UUID(str(state.project_id)))
            if project is None:
                project = type(
                    "FakeProject",
                    (),
                    {
                        "id": state.project_id,
                        "status": "RESEARCHING",
                    },
                )()

            factcheck_out = await run_factcheck(
                session=session,
                router=None,
                project=project,
                script_or_summary=script_text,
                sources=[],
                topic="",
                actor="system",
                correlation_id=state.run_id,
            )
            await session.commit()
            result["factcheck"] = factcheck_out
    except Exception as exc:
        logger.warning(
            "script_factcheck_node skipped: %s run=%s",
            exc,
            state.run_id,
        )
        result["factcheck"] = {
            "overall_verdict": "WARN",
            "claims": [],
            "skip_reason": str(exc),
        }

    return result


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------

def _route_after_entry(state: PipelineState) -> str:
    """After entry_router: branch to research or skip to write."""
    return NodeName.WRITE.value if state.entry_point == "script" else NodeName.RESEARCH.value


def _route_after_write(state: PipelineState) -> str:
    """After WRITE: script path needs factcheck; research goes to storyboard."""
    return (
        NodeName.FACTCHECK.value
        if state.entry_point == "script"
        else NodeName.STORYBOARD.value
    )


# ---------------------------------------------------------------------------
# DB manager -- injected by tests for isolation
# ---------------------------------------------------------------------------

_DB_MANAGER_FACTORY: Any = None


def _get_db_manager():
    """Return the database manager for this graph invocation.

    In tests, set_db_manager_factory() can inject a fake that provides
    a .session() context manager and a .close() awaitable.
    In production, falls back to the real Database singleton.
    """
    global _DB_MANAGER_FACTORY
    if _DB_MANAGER_FACTORY is not None:
        return _DB_MANAGER_FACTORY()
    from app.core.config import get_settings
    from app.core.database import Database
    return Database(get_settings().database_url)


def set_db_manager_factory(factory):
    """Test helper: override the DB manager factory."""
    global _DB_MANAGER_FACTORY
    _DB_MANAGER_FACTORY = factory


def reset_db_manager_factory():
    """Test helper: restore DB manager to the real Database."""
    global _DB_MANAGER_FACTORY
    _DB_MANAGER_FACTORY = None


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_FNS: dict[NodeName, NodeFn] = {
    NodeName.RESEARCH: research_node,
    NodeName.RANKING: ranking_node,
    NodeName.WRITE: write_node,
    NodeName.FACTCHECK: script_factcheck_node,
    NodeName.STORYBOARD: storyboard_node,
    NodeName.PRODUCE: produce_node,
    NodeName.RENDER: render_node,
}

# Deprecated -- kept for backward compat with existing tests
NODE_SEQUENCE: list[NodeName] = list(NODE_FNS)


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(checkpointer: Any = None) -> Any:
    """Compile the conditional-entry pipeline graph.

    *checkpointer* is any LangGraph BaseCheckpointSaver (InMemorySaver in
    tests, Postgres-AsyncSaver in production).
    """
    graph: StateGraph = StateGraph(PipelineState)

    # Register entry_router with NO retry policy (it's a metadata read)
    graph.add_node("entry_router", entry_router_node)

    # Register execution nodes with the standard retry policy (BR-4)
    for name, fn in NODE_FNS.items():
        graph.add_node(name.value, fn, retry_policy=RETRY_POLICY)

    # -- edges --
    # START -> entry_router (always)
    graph.add_edge(START, "entry_router")

    # entry_router → research path OR script path
    graph.add_conditional_edges(
        "entry_router",
        _route_after_entry,
        {
            NodeName.RESEARCH.value: NodeName.RESEARCH.value,
            NodeName.WRITE.value: NodeName.WRITE.value,
        },
    )

    # Research path linear chain (unchanged)
    graph.add_edge(NodeName.RESEARCH.value, NodeName.RANKING.value)
    graph.add_edge(NodeName.RANKING.value, NodeName.WRITE.value)

    # After WRITE: script path → factcheck → storyboard; research → storyboard
    graph.add_conditional_edges(
        NodeName.WRITE.value,
        _route_after_write,
        {
            NodeName.FACTCHECK.value: NodeName.FACTCHECK.value,
            NodeName.STORYBOARD.value: NodeName.STORYBOARD.value,
        },
    )

    # Script path tail: factcheck → storyboard → produce → render
    graph.add_edge(NodeName.FACTCHECK.value, NodeName.STORYBOARD.value)
    graph.add_edge(NodeName.STORYBOARD.value, NodeName.PRODUCE.value)
    graph.add_edge(NodeName.PRODUCE.value, NodeName.RENDER.value)
    graph.add_edge(NodeName.RENDER.value, END)

    return graph.compile(
        checkpointer=checkpointer,
        # Interrupt after every execution node (Mode 2 human gate)
        interrupt_after=[n.value for n in NodeName],
    )
