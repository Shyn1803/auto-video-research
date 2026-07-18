"""Task 4-2 Step 5 (BR-4) -- CI guard against hardcoded prompt strings."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

from check_no_hardcoded_prompts import find_hardcoded_prompts  # noqa: E402


def test_clean_pipeline_tree_has_no_offenses():
    offenses = find_hardcoded_prompts()
    assert offenses == []


def test_deliberately_inlined_prompt_is_detected(tmp_path):
    fake_pipeline = tmp_path / "pipeline"
    fake_pipeline.mkdir()
    (fake_pipeline / "nodes").mkdir()
    (fake_pipeline / "nodes" / "bad_node.py").write_text(
        'PROMPT = "Ban la tro ly. {{ topic }} hay lam gi do."\n',
        encoding="utf-8",
    )
    offenses = find_hardcoded_prompts(pipeline_dir=fake_pipeline)
    assert len(offenses) == 1
    assert offenses[0][0].endswith("bad_node.py")


def test_seed_templates_directory_is_excluded():
    """app/pipeline/prompts/seed.py legitimately holds Jinja2 templates --
    the guard must not flag its own seed data."""
    offenses = find_hardcoded_prompts()
    assert not any("prompts" + "\\seed.py" in f or "prompts/seed.py" in f for f, _, _ in offenses)
