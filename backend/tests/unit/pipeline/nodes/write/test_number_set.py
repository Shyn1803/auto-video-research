"""Unit tests -- Task 4-5 Step 4 (number-set normalization + subset check).

Flagged in the task file as the highest-scrutiny unit test in this task:
normalization must treat "92,5" (VN decimal comma), "92.5" (dot), and the
spelled-out Vietnamese words as the *same* number before comparing sets.
"""

from __future__ import annotations

from app.pipeline.nodes.write.validators import (
    check_number_subset,
    normalize_numbers,
)


def test_normalize_comma_and_dot_decimal_are_equal():
    assert normalize_numbers("Đạt 92,5% hiệu suất") == {"92.5"}
    assert normalize_numbers("Đạt 92.5% hiệu suất") == {"92.5"}


def test_normalize_spelled_out_vietnamese_decimal():
    assert normalize_numbers("chín mươi hai phẩy năm phần trăm") == {"92.5"}


def test_normalize_spelled_out_integer():
    assert normalize_numbers("một trăm người dùng") == {"100"}
    assert normalize_numbers("mười hai mô hình") == {"12"}
    assert normalize_numbers("hai mươi lăm bài test") == {"25"}


def test_normalize_trailing_zero_stripped():
    assert normalize_numbers("92,50%") == {"92.5"}


def test_normalize_plain_integer_digit_form():
    assert normalize_numbers("có 5 mô hình mới") == {"5"}


def test_subset_check_passes_when_all_outline_numbers_in_script():
    outline = "Model đạt 92,5% điểm benchmark, ra mắt năm 2026."
    script = "Model này đạt chín mươi hai phẩy năm phần trăm điểm, ra mắt 2026."
    result = check_number_subset(outline, script)
    assert result.ok is True
    assert result.missing == frozenset()


def test_subset_check_fails_when_a_number_is_dropped():
    outline = "Model đạt 92,5% điểm, giá 199 đô la."
    script = "Model đạt 92.5% điểm."
    result = check_number_subset(outline, script)
    assert result.ok is False
    assert "199" in result.missing


def test_subset_check_mixed_formats_still_match():
    outline = "Tăng 30% trong quý này."
    script = "Tăng ba mươi phần trăm trong quý này."
    result = check_number_subset(outline, script)
    assert result.ok is True
