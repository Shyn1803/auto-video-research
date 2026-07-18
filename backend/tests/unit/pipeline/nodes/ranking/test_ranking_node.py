"""Task 4-4 Step 2 -- ranking node: configurable weights, score/reason written back."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.ranking.node import rank_sources
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
    def __init__(self, prompt_version):
        self._version = prompt_version

    async def execute(self, _stmt):
        return _Result(self._version)


def _prompt_version():
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template=(
            "{{ topic }} {{ today }} {{ w_recency }} {{ w_relevance }} "
            "{{ w_trust }} {{ w_confirm }} {{ sources_json }}"
        ),
        variables=["topic", "today", "w_recency", "w_relevance", "w_trust", "w_confirm", "sources_json"],
        is_active=True, created_by="system",
    )


class FakeRouter:
    def __init__(self, rankings):
        self.rankings = rankings
        self.last_prompt = None

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.last_prompt = args[0]
        return {"rankings": self.rankings}


@pytest.mark.asyncio
async def test_rank_sources_writes_score_and_reason_back():
    session = FakeSession(_prompt_version())
    router = FakeRouter([
        {"source_id": "s1", "score": 85, "reason_vi": "Nguon moi va lien quan"},
        {"source_id": "s2", "score": 40, "reason_vi": "Khong trusted"},
    ])
    sources = [{"id": "s1", "title": "A"}, {"id": "s2", "title": "B"}]

    result = await rank_sources(
        session, router, sources, "AI news",
        weight_recency=0.3, weight_relevance=0.3, weight_trust=0.25, weight_confirm=0.15,
    )

    assert result[0]["score"] == 85
    assert result[0]["reason"] == "Nguon moi va lien quan"
    assert result[1]["score"] == 40


@pytest.mark.asyncio
async def test_rank_sources_weights_are_not_hardcoded_in_prompt_call():
    """Weights actually flow through to the rendered prompt -- not baked
    into the template itself (rules/performance.md)."""
    session = FakeSession(_prompt_version())
    router = FakeRouter([])
    sources = [{"id": "s1", "title": "A"}]

    await rank_sources(
        session, router, sources, "topic",
        weight_recency=0.5, weight_relevance=0.2, weight_trust=0.2, weight_confirm=0.1,
    )
    assert "0.5" in router.last_prompt
    assert "0.2" in router.last_prompt


@pytest.mark.asyncio
async def test_rank_sources_missing_ranking_defaults_to_none_score():
    session = FakeSession(_prompt_version())
    router = FakeRouter([{"source_id": "s1", "score": 90}])
    sources = [{"id": "s1"}, {"id": "s2"}]  # s2 not returned by the LLM

    result = await rank_sources(
        session, router, sources, "topic",
        weight_recency=0.3, weight_relevance=0.3, weight_trust=0.25, weight_confirm=0.15,
    )
    assert result[1]["score"] is None


@pytest.mark.asyncio
async def test_rank_sources_raises_when_prompt_not_seeded():
    session = FakeSession(None)
    router = FakeRouter([])
    with pytest.raises(RuntimeError, match="not seeded"):
        await rank_sources(
            session, router, [], "topic",
            weight_recency=0.3, weight_relevance=0.3, weight_trust=0.25, weight_confirm=0.15,
        )
