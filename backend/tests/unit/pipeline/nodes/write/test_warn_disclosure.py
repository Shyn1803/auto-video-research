"""Unit tests -- Task 4-5 Step 7 (BR-4 WARN-claim disclosure presence validator)."""

from __future__ import annotations

from app.pipeline.nodes.write.validators import (
    DISCLOSURE_PHRASE,
    check_warn_claim_disclosure,
)


def test_warn_claim_used_with_disclosure_present_no_warning():
    warn_claims = [{"claim_text": "Giá bán lẻ dự kiến tăng mạnh"}]
    voice_over = (
        f"Giá bán lẻ dự kiến tăng mạnh, {DISCLOSURE_PHRASE}. "
        "Phần tiếp theo nói về công nghệ mới."
    )
    warnings = check_warn_claim_disclosure(voice_over, warn_claims)
    assert warnings == []


def test_warn_claim_used_without_disclosure_flagged():
    warn_claims = [{"claim_text": "Giá bán lẻ dự kiến tăng mạnh"}]
    voice_over = "Giá bán lẻ dự kiến tăng mạnh trong năm tới. Phần tiếp theo khác."
    warnings = check_warn_claim_disclosure(voice_over, warn_claims)
    assert len(warnings) == 1
    assert warnings[0].type == "warn_claim_disclosure_missing"


def test_warn_claim_not_used_in_script_no_warning():
    warn_claims = [{"claim_text": "Một tuyên bố hoàn toàn không liên quan tới nội dung"}]
    voice_over = "Nội dung script không nhắc gì tới điều đó cả."
    warnings = check_warn_claim_disclosure(voice_over, warn_claims)
    assert warnings == []


def test_multiple_warn_claims_only_undisclosed_ones_flagged():
    warn_claims = [
        {"claim_text": "Giá bán lẻ dự kiến tăng mạnh"},
        {"claim_text": "Hiệu suất mô hình vượt trội đối thủ cạnh tranh"},
    ]
    voice_over = (
        f"Giá bán lẻ dự kiến tăng mạnh, {DISCLOSURE_PHRASE}. "
        "Hiệu suất mô hình vượt trội đối thủ cạnh tranh trong năm nay."
    )
    warnings = check_warn_claim_disclosure(voice_over, warn_claims)
    assert len(warnings) == 1
    assert "Hiệu suất mô hình vượt trội" in warnings[0].detail
