"""Unit tests -- Task 4-5 Step 4 (script node: happy path + retry-then-warn)."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.write.script import generate_script
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
        template="{{ topic }} {{ outline_json }} {{ target_duration_s }}",
        variables=["topic", "outline_json", "target_duration_s"],
        is_active=True, created_by="system",
    )


_OUTLINE = {"hook": "Đạt 92,5% hiệu suất", "cta": "Theo dõi kênh"}


class FakeRouter:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        response = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return response


@pytest.mark.asyncio
async def test_happy_path_numbers_match_no_warnings():
    session = FakeSession(_prompt_version())
    router = FakeRouter([
        {
            "title": "Tiêu đề ngắn",
            "description": "Mô tả",
            "tags": ["ai"],
            "voice_over": "Đạt chín mươi hai phẩy năm phần trăm hiệu suất. Theo dõi kênh.",
            "estimated_duration_s": 60,
        }
    ])

    result = await generate_script(
        session, router,
        topic="AI news", outline=_OUTLINE, outline_version=3, target_duration_s=60,
    )

    assert result["warnings"] == []
    assert result["source_outline_version"] == 3
    assert router.calls == 1


@pytest.mark.asyncio
async def test_number_mismatch_retries_once_then_warns():
    session = FakeSession(_prompt_version())
    bad_response = {
        "title": "T",
        "description": "D",
        "tags": [],
        "voice_over": "Không có số liệu nào ở đây.",
        "estimated_duration_s": 60,
    }
    router = FakeRouter([bad_response, bad_response])

    result = await generate_script(
        session, router,
        topic="t", outline=_OUTLINE, outline_version=1, target_duration_s=60,
    )

    assert router.calls == 2  # exactly one retry, not more
    types = [w["type"] for w in result["warnings"]]
    assert "number_set_mismatch" in types


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt_no_warning():
    session = FakeSession(_prompt_version())
    bad = {
        "title": "T", "description": "D", "tags": [],
        "voice_over": "không có số nào",
        "estimated_duration_s": 60,
    }
    good = {
        "title": "T", "description": "D", "tags": [],
        "voice_over": "Đạt chín mươi hai phẩy năm phần trăm hiệu suất",
        "estimated_duration_s": 60,
    }
    router = FakeRouter([bad, good])

    result = await generate_script(
        session, router,
        topic="t", outline=_OUTLINE, outline_version=1, target_duration_s=60,
    )

    assert router.calls == 2
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_raises_when_prompt_not_seeded():
    session = FakeSession(None)
    router = FakeRouter([{}])
    with pytest.raises(RuntimeError, match="not seeded"):
        await generate_script(
            session, router,
            topic="t", outline=_OUTLINE, outline_version=1, target_duration_s=60,
        )
