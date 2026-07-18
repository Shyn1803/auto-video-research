"""Unit tests -- Task 4-5 Step 3 (outline node, AC1 happy path + BR-1 tie-in)."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.write.outline import (
    MANDATORY_SECTIONS,
    generate_outline,
    sections_missing_source_citation,
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
    def __init__(self, prompt_version):
        self._version = prompt_version

    async def execute(self, _stmt):
        return _Result(self._version)


def _prompt_version():
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template="{{ topic }} {{ ranked_summaries }} {{ target_duration_s }} {{ claims_passed }}",
        variables=["topic", "ranked_summaries", "target_duration_s", "claims_passed"],
        is_active=True, created_by="system",
    )


_FULL_OUTLINE = {
    "hook": "92,5% mô hình mới nhanh hơn [s1]",
    "introduction": "Giới thiệu bối cảnh [s1]",
    "problem": "Vấn đề hiện tại [s2]",
    "controversy": None,
    "solution": "Giải pháp đề xuất [s1]",
    "demo": "Ví dụ minh hoạ cụ thể [s3]",
    "conclusion": "Tổng kết [s2]",
    "cta": "Theo dõi kênh để cập nhật [s1]",
}


class FakeRouter:
    def __init__(self, outline):
        self.outline = outline
        self.last_prompt = None

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.last_prompt = args[0]
        return {"outline": self.outline}


@pytest.mark.asyncio
async def test_outline_has_7_sections_each_with_source_citation():
    session = FakeSession(_prompt_version())
    router = FakeRouter(_FULL_OUTLINE)

    result = await generate_outline(
        session, router,
        topic="AI news", ranked_summaries="tóm tắt...", target_duration_s=60,
        claims_passed=[{"claim_text": "Model X đạt 92,5% benchmark"}],
    )

    outline = result["outline"]
    for key in MANDATORY_SECTIONS:
        assert outline[key], f"section {key} must not be empty"
        assert "[" in outline[key] and "]" in outline[key]
    assert len(MANDATORY_SECTIONS) == 7
    assert outline["controversy"] is None


@pytest.mark.asyncio
async def test_missing_citation_detected():
    incomplete = {**_FULL_OUTLINE, "demo": "Ví dụ minh hoạ không trích nguồn"}
    missing = sections_missing_source_citation(incomplete)
    assert missing == ["demo"]


@pytest.mark.asyncio
async def test_outline_raises_when_prompt_not_seeded():
    session = FakeSession(None)
    router = FakeRouter(_FULL_OUTLINE)
    with pytest.raises(RuntimeError, match="not seeded"):
        await generate_outline(
            session, router,
            topic="t", ranked_summaries="r", target_duration_s=60, claims_passed=[],
        )
