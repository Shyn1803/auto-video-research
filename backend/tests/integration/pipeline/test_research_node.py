"""Task 4-3 Step 8 -- full research pipeline AC1 (12 articles -> 10 sources,
partial_content marked) and AC3 (re-run same topic -> 0 re-crawl).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderSettings, SearchAdapter
from app.adapters.registry import register_search
from app.models.prompt import PromptVersion
from app.models.source import Source
from app.pipeline.nodes.research.run import run_research
from app.services.prompt_render import invalidate_all

_FULL_ARTICLE = """
<html><head><title>{title}</title></head><body><article>
<h1>{title}</h1>
<p>{title} brings meaningful improvements across several benchmark suites.
Independent researchers reproduced the reported numbers and confirmed
consistent gains in accuracy and latency across a wide range of tasks,
noting the training pipeline documentation was unusually thorough for an
industry release, which helped the reproduction effort considerably this
time around compared to prior similar announcements from other labs.</p>
</article></body></html>
"""

_PAYWALL_ARTICLE = """
<html><head><title>Exclusive Report</title></head><body><article>
<h1>Exclusive Report</h1><p>Subscribe to continue reading.</p>
</article></body></html>
"""

# 12 raw hits total, 2 of which are exact-URL repeats ("2 trung") of hits
# already counted, 1 paywalled -> 10 unique sources after url_hash dedupe:
# connector A: a1..a7 (7 unique) + dup1 + dup2 = 9 hits
# connector B: dup1 (repeat) + dup2 (repeat) + paywall = 3 hits
# unique = a1..a7 (7) + dup1 + dup2 + paywall = 10
_HITS_CONNECTOR_A = [
    {"title": f"Article {i}", "url": f"https://news.example.com/a{i}", "snippet": "", "provider": "fake_a"}
    for i in range(1, 8)
] + [
    {"title": "Duplicate One", "url": "https://news.example.com/dup1", "snippet": "", "provider": "fake_a"},
    {"title": "Duplicate Two", "url": "https://news.example.com/dup2", "snippet": "", "provider": "fake_a"},
]
_HITS_CONNECTOR_B = [
    {"title": "Duplicate One", "url": "https://news.example.com/dup1", "snippet": "", "provider": "fake_b"},
    {"title": "Duplicate Two", "url": "https://news.example.com/dup2", "snippet": "", "provider": "fake_b"},
    {"title": "Exclusive Report", "url": "https://news.example.com/paywall", "snippet": "", "provider": "fake_b"},
]


@register_search("research_fixture_a")
class _FixtureConnectorA(SearchAdapter):
    name = "research_fixture_a"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        return [dict(h) for h in _HITS_CONNECTOR_A]


@register_search("research_fixture_b")
class _FixtureConnectorB(SearchAdapter):
    name = "research_fixture_b"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        return [dict(h) for h in _HITS_CONNECTOR_B]


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeResearchSession:
    """In-memory Source table -- backs cache.get_cached_source/upsert_cache_entry
    realistically across multiple run_research() calls (needed for AC3)."""

    def __init__(self):
        self.sources: list[Source] = []
        self.prompt_version = PromptVersion(
            id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
            template="Tom tat {{ topic }}: {{ article_title }} - {{ article_content }} ({{ source_url }})",
            variables=["topic", "article_title", "article_content", "source_url"],
            is_active=True, created_by="system",
        )

    async def execute(self, stmt):
        compiled_str = str(stmt).lower()
        if "from prompt_versions" in compiled_str:
            return _Result(self.prompt_version)
        # sources query (cache.get_cached_source)
        params = stmt.compile().params
        wanted_hash = params.get("url_hash_1", params.get("url_hash"))
        cutoff = params.get("fetched_at_1", params.get("fetched_at"))
        for row in self.sources:
            if row.project_id is not None or row.url_hash != wanted_hash:
                continue
            if cutoff is not None and row.fetched_at < cutoff:
                continue
            return _Result(row)
        return _Result(None)

    def add(self, obj):
        if isinstance(obj, Source):
            self.sources.append(obj)

    async def flush(self):
        for obj in self.sources:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "fetched_at", None) is None:
                obj.fetched_at = datetime.now(UTC)


class FakeRouter:
    def __init__(self):
        self.call_count = 0

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.call_count += 1
        return {"summary_vi": "Tom tat.", "key_facts": ["fact"], "relevance_to_topic": 7}


def _mock_all_crawls():
    respx.get(url__regex=r"https://news\.example\.com/robots\.txt").mock(return_value=Response(404))
    for i in range(1, 8):
        respx.get(f"https://news.example.com/a{i}").mock(
            return_value=Response(200, text=_FULL_ARTICLE.format(title=f"Article {i}"))
        )
    respx.get("https://news.example.com/dup1").mock(
        return_value=Response(200, text=_FULL_ARTICLE.format(title="Duplicate One"))
    )
    respx.get("https://news.example.com/dup2").mock(
        return_value=Response(200, text=_FULL_ARTICLE.format(title="Duplicate Two"))
    )
    respx.get("https://news.example.com/paywall").mock(
        return_value=Response(200, text=_PAYWALL_ARTICLE)
    )


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


@pytest.mark.asyncio
@respx.mock
async def test_ac1_twelve_hits_two_duplicates_one_paywall_yields_ten_sources():
    _mock_all_crawls()
    session = FakeResearchSession()
    router = FakeRouter()

    result = await run_research(
        session, router, "AI benchmarks",
        connector_names=["research_fixture_a", "research_fixture_b"],
    )

    assert result["total_sources"] == 10
    paywalled = [s for s in result["sources"] if s["url"] == "https://news.example.com/paywall"]
    assert len(paywalled) == 1
    assert paywalled[0]["partial_content"] is True
    assert result["summarized_ok"] >= 5  # BR-5 quality bar


@pytest.mark.asyncio
@respx.mock
async def test_ac3_rerun_same_topic_zero_recrawl():
    _mock_all_crawls()
    session = FakeResearchSession()
    router = FakeRouter()

    await run_research(
        session, router, "AI benchmarks",
        connector_names=["research_fixture_a", "research_fixture_b"],
    )
    crawl_calls_after_first_run = sum(
        1 for call in respx.calls if "robots.txt" not in str(call.request.url)
    )

    # Second run: same URLs should all be served from the shared cache
    # (project_id NULL, within TTL) -- no new crawl HTTP calls.
    await run_research(
        session, router, "AI benchmarks",
        connector_names=["research_fixture_a", "research_fixture_b"],
    )
    crawl_calls_after_second_run = sum(
        1 for call in respx.calls if "robots.txt" not in str(call.request.url)
    )

    assert crawl_calls_after_second_run == crawl_calls_after_first_run
