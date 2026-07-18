"""Task 4-3 Step 7 + task 5-10 Step 2 -- run_research + AI summary generation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.research.run import (
    _build_ranked_summaries,
    _generate_ai_summary,
    run_research,
)
from app.services.prompt_render import invalidate_all


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


# ── helpers ───────────────────────────────────────────────────────────────────

def _prompt_version(template="Output JSON: {ai_summary: T}", variables=None):
    return PromptVersion(
        id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        version=1,
        template=template,
        variables=variables or ["topic", "ranked_summaries"],
        is_active=True,
        created_by="system",
    )


class _FakeExecute:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, prompt_version=None):
        self._pv = prompt_version

    async def execute(self, _stmt):
        return _FakeExecute(self._pv)


class FakeRouter:
    def __init__(self, summary_text="AI summary"):
        self.summary_text = summary_text
        self.calls: list = []

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.calls.append((capability, method, tier, args))
        return {"ai_summary": self.summary_text}


# ── _build_ranked_summaries ────────────────────────────────────────────────────

def test_build_ranked_summaries_skips_failed():
    sources = [
        {"title": "A", "summary_vi": "S1", "key_facts": ["f1"], "summarize_failed": False},
        {"title": "B", "summary_vi": None, "key_facts": [], "summarize_failed": True},
    ]
    text = _build_ranked_summaries(sources)
    assert "Nguồn 1: A" in text
    assert "Nguồn 2: B" not in text


def test_build_ranked_summaries_empty():
    assert _build_ranked_summaries([]) == "(không có nguồn tóm tắt thành công)"


# ── _generate_ai_summary ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_summary_success():
    session = FakeSession(_prompt_version())
    router = FakeRouter(summary_text="AI summary two sentence.")
    result = await _generate_ai_summary(session, router, "AI", [], correlation_id="run-1")
    assert result == "AI summary two sentence."
    assert len(router.calls) == 1
    cap, method, tier, args = router.calls[0]
    assert cap == "llm"
    assert method == "call_structured"
    assert tier == "cheap"


@pytest.mark.asyncio
async def test_ai_summary_strips_quotes():
    session = FakeSession(_prompt_version())
    router = FakeRouter(summary_text='"Wrapped in quotes."')
    result = await _generate_ai_summary(session, router, "T", [])
    assert result == "Wrapped in quotes."


@pytest.mark.asyncio
async def test_ai_summary_no_prompt_returns_none():
    session = FakeSession(prompt_version=None)
    router = FakeRouter()
    result = await _generate_ai_summary(session, router, "T", [])
    assert result is None
    assert router.calls == []


@pytest.mark.asyncio
async def test_ai_summary_llm_failure_returns_none():
    session = FakeSession(_prompt_version())
    router = MagicMock()
    router.call = AsyncMock(side_effect=RuntimeError("LLM down"))
    result = await _generate_ai_summary(session, router, "T", [])
    assert result is None


@pytest.mark.asyncio
async def test_ai_summary_empty_text_returns_none():
    session = FakeSession(_prompt_version())
    router = FakeRouter(summary_text="   ")
    result = await _generate_ai_summary(session, router, "T", [])
    assert result is None


# ── run_research includes ai_summary key ──────────────────────────────────────

@pytest.mark.asyncio
async def test_run_research_includes_ai_summary(monkeypatch):
    captured = {}

    async def _fake_collect(*a, **kw):
        return [{"url": "http://x", "title": "X"}], {}

    async def _fake_generate(session, router, topic, summarized, *, correlation_id=""):
        captured["called"] = True
        return "AI summary two sentence."

    monkeypatch.setattr("app.pipeline.nodes.research.run.collect_sources", _fake_collect)
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run._generate_ai_summary", _fake_generate
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.dedupe_by_url_hash", lambda c: c
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.cap_sources", lambda c, max_n=20: c
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.get_cached_source", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.upsert_cache_entry", AsyncMock()
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.crawl_url",
        AsyncMock(return_value=MagicMock(title="X", content="content", partial_content=False)),
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.summarize_sources",
        AsyncMock(return_value=[{"url": "http://x", "summarize_failed": False}]),
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.count_successful", lambda r: 1
    )

    result = await run_research(MagicMock(), MagicMock(), "AI", run_id="run-1")
    assert "ai_summary" in result
    assert result["ai_summary"] == "AI summary two sentence."
    assert captured["called"]


@pytest.mark.asyncio
async def test_run_research_ai_summary_none_on_failure(monkeypatch):
    """Non-fatal LLM failure stores None; the run still succeeds."""

    async def _fake_collect(*a, **kw):
        return [{"url": "http://x", "title": "X"}], {}

    async def _fake_generate(*a, **kw):
        return None

    monkeypatch.setattr("app.pipeline.nodes.research.run.collect_sources", _fake_collect)
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run._generate_ai_summary", _fake_generate
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.dedupe_by_url_hash", lambda c: c
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.cap_sources", lambda c, max_n=20: c
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.get_cached_source", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.upsert_cache_entry", AsyncMock()
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.crawl_url",
        AsyncMock(return_value=MagicMock(title="X", content="content", partial_content=False)),
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.summarize_sources",
        AsyncMock(return_value=[{"url": "http://x", "summarize_failed": False}]),
    )
    monkeypatch.setattr(
        "app.pipeline.nodes.research.run.count_successful", lambda r: 1
    )

    result = await run_research(MagicMock(), MagicMock(), "AI", run_id="run-1")
    assert result["ai_summary"] is None
    assert result["sources"] is not None
