"""Unit tests -- Task 4-5 Step 5 (BR-2 voice_over symbol-leak validator)."""

from __future__ import annotations

from app.pipeline.nodes.write.validators import check_voice_over_symbol_leak


def test_percent_symbol_leak_emits_warning():
    warning = check_voice_over_symbol_leak("Đạt 92%  hiệu suất")
    assert warning is not None
    assert warning.type == "voice_over_symbol_leak"
    assert "%" in warning.detail


def test_dollar_symbol_leak_emits_warning():
    warning = check_voice_over_symbol_leak("Giá $199")
    assert warning is not None
    assert warning.type == "voice_over_symbol_leak"


def test_clean_voice_over_no_warning():
    warning = check_voice_over_symbol_leak("Đạt chín mươi hai phẩy năm phần trăm hiệu suất")
    assert warning is None
