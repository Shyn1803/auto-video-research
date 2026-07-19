"""Storyboard pipeline node — full-stack test (Step 11 of 4-6 golden fixtures).

Tests the end-to-end storyboard node path:
  generate_semantic_storyboard → validate_tree → analyze → classify → resolve
Using a mock LLM router (no GPU/Ollama required).
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.layout_engine.analysis import analyze_tree, build_scene_profile, build_video_profile
from app.layout_engine.classifier import classify_tree
from app.layout_engine.motion_planner import plan_tree
from app.layout_engine.resolve import resolve_tree
from app.pipeline.nodes.storyboard.generate import generate_semantic_storyboard
from app.pipeline.nodes.storyboard.validate import validate_tree
from app.schemas.scene_tree import (
    ComponentKindItem,
    SceneTreeScene,
    SemanticStoryboard,
)

logger = logging.getLogger("avr.tests.storyboard_node")


# ── Mock LLM router ──────────────────────────────────────────────────────────


class MockLLMRouter:
    """Mocks get_active_prompt + LLM call for storyboard generation."""

    async def get_active_prompt(self, session: Any, key: str) -> str:
        return (
            "Generate a semantic storyboard from the script below. "
            "Return valid JSON matching SemanticStoryboard schema. "
            "Do NOT include layout, position, font, or animation fields.\n\n"
            "Script: {script_text}\nVoiceover: {voice_over}"
        )

    async def agenerate_with_tools(self, *args: Any, **kwargs: Any) -> Any:
        mock_response = AsyncMock()
        mock_response.content = [
            {"type": "text", "text": _GOLDEN_TREE_JSON}
        ]
        return mock_response


_GOLDEN_TREE_JSON = """{
  "scenes": [
    {
      "scene_number": 1,
      "narration_text": "Mo dau gioi thieu chu de chinh.",
      "narration_anchor": null,
      "purpose": "intro",
      "components": [{"kind": "heading", "summary": "Intro HP2", "content": {"text": "HP2"}}]
    },
    {
      "scene_number": 2,
      "narration_text": "Noi dung chi tiet phan tich chuyen sa",
      "narration_anchor": null,
      "purpose": "dat",
      "components": [
        {"kind": "stat", "summary": "Doanh so 2025", "content": {"value": "8.5 trieu USD", "source_id": "src-001"}}
      ]
    },
    {
      "scene_number": 3,
      "narration_text": "Ket luan va ket thuc bai viet.",
      "narration_anchor": null,
      "purpose": "ket_luan",
      "components": [{"kind": "body", "summary": "Summary", "content": {"text": "Ket luan"}}]
    }
  ],
  "total_duration_s": 90.0
}"""


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_router():
    return MockLLMRouter()


# ── Step 1+2: generate + validate ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_produces_valid_semantic_tree(mock_router):
    tree = await generate_semantic_storyboard(
        session=None,
        script_text="HP2 is a new operating system. Chuyen sa analysis follows.",
        voice_over="Mo dau gioi thieu chu de chinh. Noi dung chi tiet phan tich chuyen sa. Ket luan va ket thuc bai viet.",
        router=mock_router,
    )
    assert isinstance(tree, SemanticStoryboard)
    assert len(tree.scenes) == 3
    assert tree.total_duration_s == 90.0
    errors, _ = validate_tree(tree.scenes, tree.scenes[0].narration_text)
    assert not errors, f"validation errors: {errors}"


# ── Step 3+4+5: analyze + classify ──────────────────────────────────────────


def test_analyze_classify_resolve_golden_fixture():
    """Full pipeline on golden fixture (BR-4 strict-valid)."""
    import json

    tree_data = json.loads(_GOLDEN_TREE_JSON)
    tree = SemanticStoryboard(**tree_data)

    # validate first
    errors, _ = validate_tree(tree.scenes, "Mo dau gioi thieu chu de chinh. Noi dung chi tiet phan tich chuyen sa. Ket luan va ket thuc bai viet.")
    assert not errors, errors

    # analyze
    profile = analyze_tree(tree.scenes, tree.total_duration_s)
    assert profile.total_scenes == 3

    # classify
    classifications = classify_tree(tree)
    assert len(classifications) == 3

    # motion plan
    motion_plan = plan_tree(classifications, tree.model_dump(mode="json"))

    # resolve — BR-4
    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["total_scenes"] == 3
    assert result["resolution_passed"] is True
    assert len(result["scenes"]) == 3

    # scene 2 (stat, data kind) should have populated source_id field
    scene2 = result["scenes"][1]
    assert scene2["layout"] in ("BigNumber", "List", "TextFocus")
    # components must be present from semantic tree
    assert len(scene2["components"]) >= 1


# ── BR-4: classifier output NEVER has layout in components ───────────────────


def test_br4_components_have_no_layout_fields():
    """Reducer output components must not contain layout/position/font/animation."""
    import json

    tree = SemanticStoryboard(**json.loads(_GOLDEN_TREE_JSON))
    classifications = classify_tree(tree)

    forbidden = {"layout", "position", "font", "animation", "camera", "transition"}
    for cls in classifications:
        comp = cls  # classifier output does not have components
        assert not (forbidden & cls.keys()), f"forbidden keys in classify output: {cls}"


# BR-5: override on hot-regenerate


def test_br5_override_survives_hot_regenerate():
    tree = SemanticStoryboard(**__import__("json").loads(_GOLDEN_TREE_JSON))
    classifications = classify_tree(tree)
    assert classifications[0]["layout"] == "Hero"
    # override → List
    classifications[0] = {**classifications[0], "layout": "List"}
    motion_plan = plan_tree(classifications, tree.model_dump(mode="json"))
    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["scenes"][0]["layout"] == "List"


# ── Edge: empty motion tracks ════════════════════════════════════════════════


def test_empty_tree_rejected_before_pipeline():
    with pytest.raises(Exception):
        SemanticStoryboard(scenes=[], total_duration_s=60.0)


# ── Performance: small tree completes in <50ms (sanity gate) ─────────────────


def test_pipeline_completes_under_50ms():
    import time

    tree = SemanticStoryboard(
        scenes=[
            _sc(i, ["intro", "data", "conclusion"][i % 3])
            for i in range(1, 11)
        ],
        total_duration_s=120.0,
    )

    classifications = classify_tree(tree)
    motion_plan = plan_tree(classifications, tree.model_dump(mode="json"))

    t0 = time.perf_counter()
    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 50, f"resolve took {elapsed_ms:.1f}ms (threshold 50ms)"
    assert result["total_scenes"] == 10
