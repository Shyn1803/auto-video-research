"""Unit tests -- Task 4-5 Step 1 (warnings[] contract normalization)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.step_version import (
    ContentWarning,
    OutlineContent,
    OutlineSections,
    ScriptContent,
)


def test_content_warning_validates_sample_payload():
    w = ContentWarning(type="voice_over_symbol_leak", detail="found '%' in voice_over")
    assert w.type == "voice_over_symbol_leak"
    assert w.detail


def test_content_warning_rejects_unknown_type():
    with pytest.raises(ValidationError):
        ContentWarning(type="not_a_real_type", detail="x")


def test_outline_content_full_sample():
    payload = {
        "outline": {
            "hook": "92,5% mô hình mới nhanh hơn [s1]",
            "introduction": "...[s1]",
            "problem": "...[s2]",
            "controversy": None,
            "solution": "...[s1]",
            "demo": "...[s3]",
            "conclusion": "...[s2]",
            "cta": "theo dõi kênh",
        },
        "warnings": [{"type": "title_truncated", "detail": "title was 80 chars"}],
    }
    parsed = OutlineContent.model_validate(payload)
    assert isinstance(parsed.outline, OutlineSections)
    assert parsed.outline.controversy is None
    assert parsed.warnings[0].type == "title_truncated"


def test_script_content_with_lineage_and_warnings():
    payload = {
        "title": "Tiêu đề",
        "description": "Mô tả video",
        "tags": ["ai", "tech"],
        "voice_over": "chín mươi hai phẩy năm phần trăm",
        "estimated_duration_s": 60,
        "source_outline_version": 2,
        "warnings": [
            {"type": "number_set_mismatch", "detail": "outline has 92.5 but script omits it"}
        ],
    }
    parsed = ScriptContent.model_validate(payload)
    assert parsed.source_outline_version == 2
    assert parsed.warnings[0].type == "number_set_mismatch"


def test_script_content_defaults_lineage_and_warnings_empty():
    payload = {
        "title": "T",
        "description": "D",
        "voice_over": "voice",
        "estimated_duration_s": 30,
    }
    parsed = ScriptContent.model_validate(payload)
    assert parsed.source_outline_version is None
    assert parsed.warnings == []
    assert parsed.tags == []
