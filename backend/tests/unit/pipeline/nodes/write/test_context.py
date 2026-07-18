"""Unit tests -- Task 4-5 Step 2 (BR-1 claim/content filtering)."""

from __future__ import annotations

from app.pipeline.nodes.write.context import build_write_context


def test_fail_claim_excluded_from_claims_passed():
    claims = [
        {"claim_text": "Model X đạt 92,5% benchmark", "verdict": "PASS"},
        {"claim_text": "Model Y ra mắt tháng 13", "verdict": "FAIL"},
    ]
    ctx = build_write_context(claims, sources=[])
    passed_texts = [c["claim_text"] for c in ctx["claims_passed"]]
    assert "Model X đạt 92,5% benchmark" in passed_texts
    assert "Model Y ra mắt tháng 13" not in passed_texts


def test_warn_claim_kept_in_claims_passed():
    claims = [{"claim_text": "Nguồn chưa xác nhận về giá", "verdict": "WARN"}]
    ctx = build_write_context(claims, sources=[])
    assert len(ctx["claims_passed"]) == 1


def test_pending_claim_excluded():
    claims = [{"claim_text": "Chưa kiểm chứng", "verdict": "PENDING"}]
    ctx = build_write_context(claims, sources=[])
    assert ctx["claims_passed"] == []


def test_source_content_containing_fail_claim_keyword_is_absent_from_context():
    claims = [{"claim_text": "GigaModel ra mắt ngày 30 tháng 13", "verdict": "FAIL"}]
    sources = [
        {"id": "s1", "summary_vi": "GigaModel ra mắt vào một ngày không có thật"},
        {"id": "s2", "summary_vi": "Thông tin hoàn toàn khác, không liên quan"},
    ]
    ctx = build_write_context(claims, sources)
    ids = [s["id"] for s in ctx["sources"]]
    assert "s1" not in ids
    assert "s2" in ids


def test_no_fail_claims_keeps_all_sources():
    claims = [{"claim_text": "Model X đạt 92,5% benchmark", "verdict": "PASS"}]
    sources = [{"id": "s1", "summary_vi": "Model X đạt 92,5% benchmark trong bài test"}]
    ctx = build_write_context(claims, sources)
    assert [s["id"] for s in ctx["sources"]] == ["s1"]
