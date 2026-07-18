"""Task 4-3 Step 7 -- research_node's LangGraph-facing wrapper.

Not wired into app/pipeline/graph.py's live NODE_FNS yet -- see the module
docstring / decisions log: swapping the stub for this DB-touching version
would break 4-1's already-passing happy-path tests (they build a real
graph and run NodeName.RESEARCH without a live DB). This test exercises
the wrapper directly, mocking Database/ProviderRouter at the point node.py
imports them, so the wiring itself is proven correct independent of that
decision.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.nodes.research import node as node_mod
from app.pipeline.state import NodeName, PipelineState


class _FakeProject:
    topic = "AI benchmarks"


@pytest.mark.asyncio
async def test_research_node_fetches_project_topic_and_returns_research_payload(monkeypatch):
    fake_session = MagicMock()
    fake_session.get = AsyncMock(return_value=_FakeProject())
    fake_session.commit = AsyncMock()

    class _SessionCM:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *exc):
            return False

    fake_db = MagicMock()
    fake_db.session = MagicMock(return_value=_SessionCM())
    fake_db.close = AsyncMock()

    monkeypatch.setattr(node_mod, "Database", lambda *_a, **_kw: fake_db, raising=False)
    monkeypatch.setattr("app.core.database.Database", lambda *_a, **_kw: fake_db)
    monkeypatch.setattr("app.core.router.ProviderRouter", lambda *_a, **_kw: SimpleNamespace())

    called_with = {}

    async def _fake_run_research(session, router, topic, **kwargs):
        called_with["topic"] = topic
        called_with["kwargs"] = kwargs
        return {"sources": [], "total_sources": 0}

    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.run_research", _fake_run_research
    )

    state = PipelineState(project_id="11111111-1111-1111-1111-111111111111", run_id="run-1")
    result = await node_mod.research_node(state)

    assert called_with["topic"] == "AI benchmarks"
    assert result["research"] == {"sources": [], "total_sources": 0}
    assert NodeName.RESEARCH in result["completed_nodes"]
    fake_db.close.assert_awaited_once()
    fake_session.commit.assert_awaited_once()
