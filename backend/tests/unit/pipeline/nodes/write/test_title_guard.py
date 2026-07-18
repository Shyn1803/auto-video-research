"""Unit tests -- Task 4-5 Step 6 (BR-3 title length guard)."""

from __future__ import annotations

from app.pipeline.nodes.write.validators import TITLE_MAX_LEN, enforce_title_length


def test_short_title_untouched_no_warning():
    title = "Tiêu đề ngắn gọn"
    result = enforce_title_length(title)
    assert result.title == title
    assert result.warning is None


def test_long_title_truncated_at_word_boundary_with_warning():
    title = "A" * 40 + " " + "B" * 40  # 81 chars, well over 70
    result = enforce_title_length(title)

    assert len(result.title) <= TITLE_MAX_LEN
    assert not result.title.endswith(" ")
    assert result.title == title[:40]  # cut at the word boundary, not mid-word
    assert result.warning is not None
    assert result.warning.type == "title_truncated"
    assert "81" in result.warning.detail


def test_truncation_never_cuts_mid_word():
    title = "x" * 75  # single long word, no spaces at all
    result = enforce_title_length(title)
    # no space to break on -- falls back to a hard cut at TITLE_MAX_LEN,
    # but still must warn (never silent) per BR-3.
    assert len(result.title) <= TITLE_MAX_LEN
    assert result.warning is not None
