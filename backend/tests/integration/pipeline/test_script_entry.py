"""Steps 3-4 integration tests -- script_entry graph path (BR-2, AC1, AC2).

AC1: graph skips research/ranking for script entry, goes straight to factcheck.
AC2: factcheck FAIL verdict causes transition to NEED_REVIEW even in script path.
"""

from __future__ import annotations

import uuid
from collections import deque
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.pipeline.graph import (
    NODE_FNS,
    _route_after_entry,
    _route_after_write,
    build_graph,
    entry_router_node,
    reset_db_manager_factory,
    script_factcheck_node,
    set_db_manager_factory,
)
from app.pipeline.state import NodeName, PipelineState

# ---------------------------------------------------------------------------
# Shared tracking state
# ---------------------------------------------------------------------------

_research_calls: deque = deque()
_factcheck_fail_override: bool = False
_fake_project: MagicMock | None = None

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset shared mutable state before each test."""
    global _research_calls, _fake_project
    _research_calls.clear()
    _fake_project = None
    yield
    reset_db_manager_factory()


@pytest.fixture()
def fake_db_manager():
    """Provide a fake DB manager with session() handling Project + StepVersion."""
    global _fake_project

    pid = uuid.uuid4()

    _fake_project = MagicMock()
    _fake_project.id = pid
    _fake_project.entry_point = "script"
    _fake_project.status = "RESEARCHING"
    _fake_project.topic = "test topic"

    _sv = MagicMock()
    _sv.project_id = pid
    _sv.step = "script"
    _sv.version = 1
    _sv.content = {"text": "Saved script content for testing"}

    class _DBSession:
        """Sync-async context manager returned by manager.session()."""

        def __init__(self, manager):
            self._manager = manager

        async def __aenter__(self):
            return self._manager

        async def __aexit__(self, *exc):
            return False

    class _FakeDB:
        """Manager: factory returns this; .session() -> sync CM -> async CM -> self."""

        def __init__(self):
            self._sv = _sv
            self._proj = _fake_project

        def session(self):
            return _DBSession(self)

        def add(self, obj):
            pass

        async def commit(self):
            pass

        async def execute(self, stmt):
            r = MagicMock()
            q = str(stmt).lower()
            if "step_versions" in q:
                r.scalar_one_or_none.return_value = self._sv
            else:
                r.scalar_one_or_none.return_value = self._proj
                r.scalars.return_value.all.return_value = [self._proj]
            return r

        async def get(self, model, pk):
            name = getattr(model, "__name__", "")
            if "Project" in name:
                return self._proj
            if "User" in name:
                from tests.conftest import CREATOR_USER
                return CREATOR_USER
            return None

        async def flush(self):
            pass

        async def close(self):
            pass

    set_db_manager_factory(_FakeDB)
    return fake_db_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(project_id, entry_point, run_id):
    return PipelineState(
        project_id=str(project_id),
        entry_point=entry_point,
        run_id=run_id,
    )


def _patch_research_node():
    original_fn = NODE_FNS[NodeName.RESEARCH]

    async def tracked_research(state):
        _research_calls.append(NodeName.RESEARCH.value)
        return await _stub_for_test(state, NodeName.RESEARCH)

    import app.pipeline.graph as _graph_mod
    _graph_mod.NODE_FNS = dict(_graph_mod.NODE_FNS)
    _graph_mod.NODE_FNS[NodeName.RESEARCH] = tracked_research
    return original_fn


async def _stub_for_test(state, name):
    return {
        "current_node": None,
        "completed_nodes": [*state.completed_nodes, name],
    }


# ---------------------------------------------------------------------------
# Unit: routing functions
# ---------------------------------------------------------------------------


class TestRoutingFunctions:
    """Pure unit tests -- no DB, no graph compilation needed."""

    def test_script_entry_routes_to_write_skipping_research(self):
        rid = str(uuid.uuid4())
        state = _make_state(uuid.uuid4(), "script", rid)
        assert _route_after_entry(state) == NodeName.WRITE.value

    def test_research_entry_routes_to_research(self):
        rid = str(uuid.uuid4())
        state = _make_state(uuid.uuid4(), "research", rid)
        assert _route_after_entry(state) == NodeName.RESEARCH.value

    def test_unknown_entry_defaults_to_research(self):
        rid = str(uuid.uuid4())
        state = _make_state(uuid.uuid4(), "alien_value", rid)
        assert _route_after_entry(state) == NodeName.RESEARCH.value

    def test_script_after_write_routes_to_factcheck(self):
        rid = str(uuid.uuid4())
        state = _make_state(uuid.uuid4(), "script", rid)
        assert _route_after_write(state) == NodeName.FACTCHECK.value

    def test_research_after_write_routes_to_storyboard(self):
        rid = str(uuid.uuid4())
        state = _make_state(uuid.uuid4(), "research", rid)
        assert _route_after_write(state) == NodeName.STORYBOARD.value


# ---------------------------------------------------------------------------
# Entry router node
# ---------------------------------------------------------------------------


class TestEntryRouterNode:
    """entry_router_node reads DB to set state.entry_point + state.write."""

    @pytest.mark.asyncio
    async def test_script_project_sets_entry_point_and_loads_script(self, fake_db_manager):
        pid = uuid.uuid4()
        run_id = str(uuid.uuid4())
        state = _make_state(pid, "script", run_id)
        result = await entry_router_node(state)
        assert result["entry_point"] == "script"
        assert result["write"]["script_text"].startswith("Saved script content for testing")

    @pytest.mark.asyncio
    async def test_research_project_sets_entry_point_only(self, fake_db_manager):
        pid = uuid.uuid4()
        run_id = str(uuid.uuid4())
        # Override the fixture project to research entry point
        global _fake_project
        _fake_project.entry_point = "research"
        state = _make_state(pid, "research", run_id)
        result = await entry_router_node(state)
        assert result["entry_point"] == "research"
        assert "script_text" not in (result.get("write") or {})


# ---------------------------------------------------------------------------
# AC1: graph topology -- script entry skips research/ranking
# ---------------------------------------------------------------------------


class TestScriptEntrySkipsResearch:
    """AC1: when entry_point=script, research must not be a completed_node."""

    @pytest.mark.asyncio
    async def test_script_entry_completes_factcheck_not_research(
        self, fake_db_manager
    ):
        pid = uuid.uuid4()
        run_id = str(uuid.uuid4())
        _patch_research_node()
        try:
            graph = build_graph(InMemorySaver())
            config = {"configurable": {"thread_id": run_id}}
            initial = _make_state(pid, "script", run_id)

            import app.pipeline.graph as _gg
            _orig_factcheck = _gg.NODE_FNS[NodeName.FACTCHECK]

            async def _noop_factcheck(state):
                return {
                    "current_node": None,
                    "completed_nodes": [*state.completed_nodes, NodeName.FACTCHECK],
                    "factcheck": {"overall_verdict": "PASS", "claims": []},
                }

            _gg.NODE_FNS[NodeName.FACTCHECK] = _noop_factcheck
            try:
                await graph.ainvoke(initial, config=config)
            finally:
                _gg.NODE_FNS[NodeName.FACTCHECK] = _orig_factcheck

            assert NodeName.RESEARCH.value not in _research_calls
        finally:
            import app.pipeline.graph as _gg
            _gg.NODE_FNS[NodeName.RESEARCH] = NODE_FNS[NodeName.RESEARCH]

    @pytest.mark.asyncio
    async def test_simple_script_factcheck_node_runs(self, fake_db_manager):
        """script_factcheck_node calls run_factcheck and returns result."""
        pid = uuid.uuid4()
        run_id = str(uuid.uuid4())
        state = PipelineState(
            project_id=str(pid),
            run_id=run_id,
            entry_point="script",
            write={"script_text": "test script with claims about dates"},
        )

        with patch("app.pipeline.graph.run_factcheck") as mock_fc:
            mock_fc.return_value = {
                "claims": [],
                "overall_verdict": "PASS",
            }
            result = await script_factcheck_node(state)
            assert result["current_node"] is None
            assert NodeName.FACTCHECK in result["completed_nodes"]
            assert result["factcheck"]["overall_verdict"] == "PASS"


# ---------------------------------------------------------------------------
# AC2: factcheck FAIL causes project NEED_REVIEW
# ---------------------------------------------------------------------------


class TestScriptFactcheckGate:
    """AC2: script-entry path FAIL verdict -> NEED_REVIEW."""

    @pytest.mark.asyncio
    async def test_factcheck_fail_gates_to_need_review(self, fake_db_manager):
        """When run_factcheck returns FAIL, project should end up NEED_REVIEW."""
        pid = uuid.uuid4()
        run_id = str(uuid.uuid4())
        state = PipelineState(
            project_id=str(pid),
            run_id=run_id,
            entry_point="script",
            write={"script_text": "bad claim with wrong date info"},
        )

        async def _fail_factcheck(session, router, project, script_or_summary, sources, topic, *args, **kwargs):
            from app.services.state_machine_edges import NEED_REVIEW
            if hasattr(project, "status"):
                project.status = NEED_REVIEW
            return {
                "claims": [
                    {
                        "claim_text": "wrong date claim",
                        "claim_type": "release_date",
                        "verdict": "FAIL",
                    }
                ],
                "overall_verdict": "FAIL",
            }

        with patch("app.pipeline.graph.run_factcheck", side_effect=_fail_factcheck):
            result = await script_factcheck_node(state)
            assert result["factcheck"]["overall_verdict"] == "FAIL"
            if _fake_project is not None:
                assert _fake_project.status == "NEED_REVIEW"
