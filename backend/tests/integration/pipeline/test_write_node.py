"""Task 4-5 Step 9 -- one integration test per Acceptance Criterion.

AC1 (happy): outline 7 sections + citations; script correct structure;
    number set matches.
AC2 (BR-1): FAIL claim excluded -> never appears in outline.
AC3 (BR-4): WARN claim used in script -> disclosure phrase present.
AC4 (BR-2,3): script number mismatch after retry -> warning (not hard
    fail); long title -> truncated + warning.
AC5 (version lineage): manual outline edit -> script generated from it
    carries that edited version as `source_outline_version`.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.write.context import build_write_context
from app.pipeline.nodes.write.outline import MANDATORY_SECTIONS, generate_outline
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


def _version(name: str, template: str, variables: list[str]) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template=template, variables=variables, is_active=True, created_by="system",
    )


class FakeSession:
    """Dispatches get_active_prompt() by name, like task 4-4's integration
    test fixture -- this write node needs both outline.generate AND
    script.generate active at once."""

    def __init__(self):
        self.versions = {
            "outline.generate": _version(
                "outline.generate",
                "{{ topic }} {{ ranked_summaries }} {{ target_duration_s }} {{ claims_passed }}",
                ["topic", "ranked_summaries", "target_duration_s", "claims_passed"],
            ),
            "script.generate": _version(
                "script.generate",
                "{{ topic }} {{ outline_json }} {{ target_duration_s }}",
                ["topic", "outline_json", "target_duration_s"],
            ),
        }

    async def execute(self, stmt):
        params = stmt.compile().params
        name = params.get("name_1", params.get("name"))
        return _Result(self.versions.get(name))


class FakeRouter:
    """Returns queued responses in order across however many `router.call`
    invocations happen (outline call, script call(s))."""

    def __init__(self, responses):
        self._queue = list(responses)
        self.calls = 0

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.calls += 1
        return self._queue.pop(0) if self._queue else self._queue[-1]


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


@pytest.mark.asyncio
async def test_ac1_happy_path_outline_and_script():
    session = FakeSession()
    router = FakeRouter([
        {"outline": _FULL_OUTLINE},
        {
            "title": "Tiêu đề ngắn",
            "description": "Mô tả video",
            "tags": ["ai"],
            "voice_over": "Đạt chín mươi hai phẩy năm phần trăm hiệu suất.",
            "estimated_duration_s": 60,
        },
    ])

    outline_content = await generate_outline(
        session, router,
        topic="AI news", ranked_summaries="tóm tắt...", target_duration_s=60,
        claims_passed=[{"claim_text": "Model X đạt 92,5% benchmark"}],
    )
    for key in MANDATORY_SECTIONS:
        assert outline_content["outline"][key]
        assert "[" in outline_content["outline"][key]

    script_content = await generate_script(
        session, router,
        topic="AI news", outline=outline_content["outline"], outline_version=1,
        target_duration_s=60,
    )
    assert script_content["warnings"] == []
    assert script_content["title"] == "Tiêu đề ngắn"
    assert script_content["estimated_duration_s"] == 60


@pytest.mark.asyncio
async def test_ac2_fail_claim_never_reaches_outline():
    claims = [
        {"claim_text": "Model X đạt 92,5% benchmark", "verdict": "PASS"},
        {"claim_text": "Model Y ra mắt ngày không có thật", "verdict": "FAIL"},
    ]
    sources = [
        {"id": "s1", "summary_vi": "Model X đạt 92,5% benchmark trong bài test"},
        {"id": "s2", "summary_vi": "Model Y ra mắt ngày không có thật theo tin đồn"},
    ]
    ctx = build_write_context(claims, sources)

    session = FakeSession()
    router = FakeRouter([{"outline": _FULL_OUTLINE}])

    outline_content = await generate_outline(
        session, router,
        topic="AI news",
        ranked_summaries="\n".join(s["summary_vi"] for s in ctx["sources"]),
        target_duration_s=60,
        claims_passed=ctx["claims_passed"],
    )

    # the FAIL claim's source never made it into ranked_summaries at all
    assert "s2" not in [s["id"] for s in ctx["sources"]]
    # and the FAIL claim itself was never in claims_passed
    passed_texts = [c["claim_text"] for c in ctx["claims_passed"]]
    assert "Model Y ra mắt ngày không có thật" not in passed_texts
    assert outline_content["outline"]["hook"]  # sanity: outline still generated


@pytest.mark.asyncio
async def test_ac3_warn_claim_used_requires_disclosure_phrase():
    session = FakeSession()
    router = FakeRouter([
        {
            "title": "T",
            "description": "D",
            "tags": [],
            "voice_over": (
                "Giá bán lẻ dự kiến tăng mạnh, theo nguồn chưa xác nhận. "
                "Phần còn lại của video."
            ),
            "estimated_duration_s": 60,
        }
    ])
    warn_claims = [{"claim_text": "Giá bán lẻ dự kiến tăng mạnh"}]

    result = await generate_script(
        session, router,
        topic="t", outline={"hook": "Giá bán lẻ dự kiến tăng mạnh [s1]"},
        outline_version=1, target_duration_s=60, warn_claims=warn_claims,
    )
    assert result["warnings"] == []

    # now without the disclosure phrase -> must be flagged
    router2 = FakeRouter([
        {
            "title": "T", "description": "D", "tags": [],
            "voice_over": "Giá bán lẻ dự kiến tăng mạnh trong năm tới.",
            "estimated_duration_s": 60,
        }
    ])
    result2 = await generate_script(
        session, router2,
        topic="t", outline={"hook": "Giá bán lẻ dự kiến tăng mạnh [s1]"},
        outline_version=1, target_duration_s=60, warn_claims=warn_claims,
    )
    types = [w["type"] for w in result2["warnings"]]
    assert "warn_claim_disclosure_missing" in types


@pytest.mark.asyncio
async def test_ac4_number_mismatch_after_retry_warns_and_long_title_truncated():
    session = FakeSession()
    long_title = "A" * 40 + " " + "B" * 40  # 81 chars
    bad_numbers_response = {
        "title": long_title,
        "description": "D",
        "tags": [],
        "voice_over": "Không có số liệu nào.",
        "estimated_duration_s": 60,
    }
    router = FakeRouter([bad_numbers_response, bad_numbers_response])

    result = await generate_script(
        session, router,
        topic="t", outline={"hook": "Đạt 92,5% hiệu suất [s1]"},
        outline_version=1, target_duration_s=60,
    )

    assert router.calls == 2  # exactly one retry, then accepted with a warning
    types = [w["type"] for w in result["warnings"]]
    assert "number_set_mismatch" in types
    assert "title_truncated" in types
    assert len(result["title"]) <= 70


@pytest.mark.asyncio
async def test_ac5_script_generated_from_manually_edited_outline_carries_its_version():
    """Simulates: outline v1 generated -> user manually edits it (would be
    persisted as outline v2 via VersioningService.manual_edit, see
    test_step_approval_service.py) -> regenerating the script must record
    that it came from the edited version (2), not the original (1)."""
    session = FakeSession()
    router = FakeRouter([
        {
            "title": "T", "description": "D", "tags": [],
            "voice_over": "Nội dung đã sửa tay.",
            "estimated_duration_s": 60,
        }
    ])

    edited_outline = {**_FULL_OUTLINE, "hook": "Hook đã sửa tay bởi người dùng [s1]"}
    edited_outline_version = 2  # the version manual_edit() produced

    script_content = await generate_script(
        session, router,
        topic="t", outline=edited_outline, outline_version=edited_outline_version,
        target_duration_s=60,
    )

    assert script_content["source_outline_version"] == 2
