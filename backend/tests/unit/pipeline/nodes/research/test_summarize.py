"""Task 4-3 Step 6 -- bounded-parallel summarize + BR-5 partial-failure handling."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.research.summarize import (
    count_successful,
    summarize_one,
    summarize_sources,
)
from app.services.prompt_render import invalidate_all


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, prompt_version: PromptVersion | None):
        self._version = prompt_version

    async def execute(self, _stmt):
        return _Result(self._version)


def _prompt_version() -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template=(
            'Tom tat: {{ topic }} - {{ article_title }} ({{ source_url }})\n{{ article_content }}'
        ),
        variables=["topic", "article_title", "article_content", "source_url"],
        is_active=True, created_by="system",
    )


class FakeRouter:
    def __init__(self, responses=None, fail_urls=None):
        self.responses = responses or {}
        self.fail_urls = fail_urls or set()
        self.calls: list[str] = []

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        prompt_text = args[0]
        self.calls.append(prompt_text)
        for url, should_fail in [(u, u in self.fail_urls) for u in self.fail_urls]:
            if url in prompt_text and should_fail:
                raise RuntimeError(f"llm call failed for {url}")
        return {
            "summary_vi": "Tom tat gia lap.",
            "key_facts": ["fact 1", "fact 2"],
            "relevance_to_topic": 8,
        }


@pytest.mark.asyncio
async def test_summarize_one_renders_prompt_and_calls_router():
    session = FakeSession(_prompt_version())
    router = FakeRouter()
    source = {"url": "https://x.com/a", "title": "T", "content": "C"}

    result = await summarize_one(session, router, source, topic="AI news")

    assert result["summary_vi"] == "Tom tat gia lap."
    assert result["summarize_failed"] is False
    assert len(router.calls) == 1
    assert "AI news" in router.calls[0]
    assert "https://x.com/a" in router.calls[0]


@pytest.mark.asyncio
async def test_summarize_one_raises_when_prompt_not_seeded():
    session = FakeSession(None)
    router = FakeRouter()
    with pytest.raises(RuntimeError, match="not seeded"):
        await summarize_one(session, router, {"url": "x"}, topic="t")


@pytest.mark.asyncio
async def test_bounded_summarize_flags_single_failure_without_raising():
    """AC1 partial: 1 of 12 summarize calls raises -> node completes, that
    source flagged, others fine."""
    session = FakeSession(_prompt_version())
    fail_url = "https://bad.com/x"
    router = FakeRouter(fail_urls={fail_url})

    sources = [{"url": f"https://ok.com/{i}", "title": "t", "content": "c"} for i in range(11)]
    sources.append({"url": fail_url, "title": "t", "content": "c"})

    results = await summarize_sources(session, router, sources, topic="AI")

    assert len(results) == 12
    failed = [r for r in results if r["summarize_failed"]]
    assert len(failed) == 1
    assert failed[0]["url"] == fail_url
    assert count_successful(results) == 11


@pytest.mark.asyncio
async def test_bounded_summarize_respects_concurrency_limit():
    """Sanity: passing concurrency=2 doesn't break correctness (no
    assertion on true parallelism timing, just that all results return)."""
    session = FakeSession(_prompt_version())
    router = FakeRouter()
    sources = [{"url": f"https://x.com/{i}", "title": "t", "content": "c"} for i in range(9)]

    results = await summarize_sources(session, router, sources, topic="AI", concurrency=2)
    assert len(results) == 9
    assert count_successful(results) == 9


@pytest.mark.asyncio
async def test_all_summarize_calls_fail_still_returns_flagged_list():
    session = FakeSession(_prompt_version())
    router = FakeRouter(fail_urls={"https://x.com/0", "https://x.com/1"})
    sources = [{"url": "https://x.com/0"}, {"url": "https://x.com/1"}]

    results = await summarize_sources(session, router, sources, topic="AI")
    assert count_successful(results) == 0
    assert all(r["summarize_failed"] for r in results)
