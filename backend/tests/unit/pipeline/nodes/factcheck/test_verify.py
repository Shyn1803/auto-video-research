"""Task 4-4 Step 4 -- verify_claim: BR-1 (independent sources), BR-2
(partial_content caps WARN), BR-4 (orphan claim -> WARN)."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.factcheck.verify import ORPHAN_MESSAGE, verify_claim
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
    def __init__(self, version):
        self._version = version

    async def execute(self, _stmt):
        return _Result(self._version)


def _prompt_version():
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template="{{ claim_text }} {{ evidence_json }}",
        variables=["claim_text", "evidence_json"],
        is_active=True, created_by="system",
    )


class FakeRouter:
    def __init__(self, response):
        self.response = response

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        return self.response


@pytest.mark.asyncio
async def test_ac5_br4_orphan_claim_returns_warn_without_calling_llm():
    """AC5/BR-4: claim with zero evidence -> WARN with exact message, no LLM call."""
    session = FakeSession(_prompt_version())
    router = FakeRouter({"verdict": "PASS", "explanation_vi": "should not be reached"})
    sources = [{"id": "s1", "url": "https://a.com/x", "content": "totally unrelated content"}]

    result = await verify_claim(session, router, "SWE-bench score", sources)

    assert result["verdict"] == "WARN"
    assert result["explanation_vi"] == ORPHAN_MESSAGE
    assert result["evidence"] == []


@pytest.mark.asyncio
async def test_ac2_br1_same_root_domain_two_articles_downgrades_pass_to_warn():
    """AC2/BR-1: 2 sources both on openai.com confirming -> WARN, not PASS."""
    session = FakeSession(_prompt_version())
    router = FakeRouter(
        {
            "verdict": "PASS",
            "supporting_source_ids": ["s1", "s2"],
            "contradicting_source_ids": [],
            "explanation_vi": "2 nguon xac nhan",
        }
    )
    sources = [
        {"id": "s1", "url": "https://openai.com/blog/a", "content": "New model reaches 92.5 percent."},
        {"id": "s2", "url": "https://openai.com/blog/b", "content": "The 92.5 percent result was confirmed."},
    ]

    result = await verify_claim(session, router, "model reaches 92.5 percent", sources)
    assert result["verdict"] == "WARN"


@pytest.mark.asyncio
async def test_br1_two_independent_domains_keeps_pass():
    session = FakeSession(_prompt_version())
    router = FakeRouter(
        {
            "verdict": "PASS",
            "supporting_source_ids": ["s1", "s2"],
            "contradicting_source_ids": [],
            "explanation_vi": "2 nguon doc lap xac nhan",
        }
    )
    sources = [
        {"id": "s1", "url": "https://openai.com/blog/a", "content": "New model reaches 92.5 percent."},
        {"id": "s2", "url": "https://techcrunch.com/b", "content": "Reports confirm 92.5 percent score."},
    ]

    result = await verify_claim(session, router, "model reaches 92.5 percent", sources)
    assert result["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_br2_partial_content_evidence_caps_at_warn():
    """A supporting source that's only partial_content (paywalled preview)
    can't carry a PASS even with 2 independent domains."""
    session = FakeSession(_prompt_version())
    router = FakeRouter(
        {
            "verdict": "PASS",
            "supporting_source_ids": ["s1", "s2"],
            "contradicting_source_ids": [],
            "explanation_vi": "2 nguon xac nhan",
        }
    )
    sources = [
        {"id": "s1", "url": "https://openai.com/a", "content": "Model reaches 92.5 percent result."},
        {
            "id": "s2", "url": "https://paywalled.com/b", "partial_content": True,
            "content": "92.5 percent result reported (subscribe for more).",
        },
    ]

    result = await verify_claim(session, router, "model reaches 92.5 percent result", sources)
    assert result["verdict"] == "WARN"


@pytest.mark.asyncio
async def test_happy_fail_verdict_two_sources_disagreeing():
    """AC1: 2 sources disagree on a release date -> claim FAIL."""
    session = FakeSession(_prompt_version())
    router = FakeRouter(
        {
            "verdict": "FAIL",
            "supporting_source_ids": ["s1"],
            "contradicting_source_ids": ["s2"],
            "explanation_vi": "2 nguon mau thuan ve ngay phat hanh",
        }
    )
    sources = [
        {"id": "s1", "url": "https://a.com/x", "content": "Released on January 15 2026."},
        {"id": "s2", "url": "https://b.com/y", "content": "Released on January 20 2026."},
    ]

    result = await verify_claim(session, router, "Released on January 15 2026", sources)
    assert result["verdict"] == "FAIL"
