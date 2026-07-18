"""Task 4-4 Step 3 -- claim extraction + claim type classification (BR-6)."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.factcheck.extract import extract_claims
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
        template="{{ script_or_summary }} {{ topic }}",
        variables=["script_or_summary", "topic"],
        is_active=True, created_by="system",
    )


class FakeRouter:
    def __init__(self, claims):
        self.claims = claims

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        return {"claims": self.claims}


@pytest.mark.asyncio
async def test_extract_only_factual_claims_correctly_typed():
    """Fixture: LLM already filtered out the 1 subjective sentence (per its
    own instruction, BR-6) -- this test verifies OUR parsing keeps exactly
    what's returned, typed correctly."""
    session = FakeSession(_prompt_version())
    router = FakeRouter([
        {"claim_text": "Model X dat 92.5% tren SWE-bench", "claim_type": "benchmark"},
        {"claim_text": "Phat hanh ngay 15/1/2026", "claim_type": "release_date"},
        {"claim_text": "Repo tai github.com/org/x", "claim_type": "github"},
    ])

    claims = await extract_claims(session, router, "text with 1 subjective sentence", "topic")

    assert len(claims) == 3
    assert claims[0]["claim_type"] == "benchmark"
    assert claims[1]["claim_type"] == "release_date"
    assert claims[2]["claim_type"] == "github"


@pytest.mark.asyncio
async def test_extract_invalid_claim_type_falls_back_to_other():
    session = FakeSession(_prompt_version())
    router = FakeRouter([{"claim_text": "Something", "claim_type": "not_a_real_type"}])

    claims = await extract_claims(session, router, "text", "topic")
    assert claims[0]["claim_type"] == "other"


@pytest.mark.asyncio
async def test_extract_skips_empty_claim_text():
    session = FakeSession(_prompt_version())
    router = FakeRouter([{"claim_text": "  ", "claim_type": "other"}, {"claim_text": "Real one", "claim_type": "version"}])

    claims = await extract_claims(session, router, "text", "topic")
    assert len(claims) == 1
    assert claims[0]["claim_text"] == "Real one"


@pytest.mark.asyncio
async def test_extract_raises_when_prompt_not_seeded():
    session = FakeSession(None)
    router = FakeRouter([])
    with pytest.raises(RuntimeError, match="not seeded"):
        await extract_claims(session, router, "text", "topic")
