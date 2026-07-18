"""Task 4-2 Step 9 -- AC4: prompt-eval comparison table across 10 topics."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.prompt_eval import build_eval_table, format_eval_table

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "eval_topics.json"
)


def _load_fixture() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_has_exactly_ten_topics():
    topics = _load_fixture()
    assert len(topics) == 10
    # long-lived asset: every row has a non-empty topic string
    assert all(t.get("topic") for t in topics)


def test_build_eval_table_renders_all_ten_topics_ok():
    template = "Ve chu de {{ topic }}, do dai {{ target_duration_s }}s."
    topics = _load_fixture()
    rows = build_eval_table(template, ["topic", "target_duration_s"], topics)

    assert len(rows) == 10
    assert all(r["parse_ok"] for r in rows)
    assert all(r["numbers_preserved"] for r in rows)  # topic digits round-trip


def test_build_eval_table_fills_missing_declared_variable_with_placeholder():
    template = "{{ persona }} noi ve {{ topic }}"
    topics = _load_fixture()
    rows = build_eval_table(template, ["persona", "topic"], topics)

    assert len(rows) == 10
    assert all(r["parse_ok"] for r in rows)


def test_format_eval_table_renders_10_data_rows_plus_header():
    template = "{{ topic }}"
    topics = _load_fixture()
    rows = build_eval_table(template, ["topic"], topics)
    table = format_eval_table(rows)

    lines = table.splitlines()
    # header + separator + 10 data rows
    assert len(lines) == 12


def test_a_render_failure_is_captured_not_raised():
    """A template referencing something that blows up at render time (e.g.
    calling an undefined filter) shows up as parse_ok=False, not a crash."""
    template = "{{ topic | this_filter_does_not_exist }}"
    topics = _load_fixture()[:2]
    rows = build_eval_table(template, ["topic"], topics)
    assert all(not r["parse_ok"] for r in rows)
    assert all(r["error"] for r in rows)
