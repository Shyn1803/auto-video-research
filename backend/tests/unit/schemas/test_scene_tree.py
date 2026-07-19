"""Tests for scene_tree.py — Step 1 of 4-6.

Covers: BR-1 (parse-fail-loud on layout fields), structural limits, sequential numbering.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.scene_tree import (
    ComponentKindItem,
    SceneTreeScene,
    SemanticStoryboard,
)

VALID_COMPONENT = {
    "kind": "heading",
    "summary": "Tiêu đề cảnh",
    "narration_anchor": "Hôm nay chúng ta sẽ tìm hiểu",
    "content": {},
    "source_id": "src_001",
}


def _make_scene(num: int = 1) -> SceneTreeScene:
    return SceneTreeScene(
        scene_number=num,
        narration_text="Hôm nay chúng ta sẽ tìm hiểu về AI.",
        narration_anchor="hôm nay",
        purpose="intro",
        components=[
            ComponentKindItem(kind="heading", summary="Tiêu đề", content={}),
        ],
    )


# BR-1: layout field in LLM output → parse fail loudly
_BR1_PAYLOADS = [
    {"kind": "body", "layout": "Hero", "summary": "text", "content": {}},
    {"kind": "stat", "position": {"x": 0, "y": 0}, "summary": "text", "content": {}},
    {"kind": "media_intent", "animation": "fade_in", "summary": "img", "content": {}},
    {"kind": "bullet", "camera": {"zoom": 1.2}, "summary": "text", "content": {}, "source_id": "s"},
]


@pytest.mark.parametrize("bad_component", _BR1_PAYLOADS)
def test_layout_field_rejected_br1(bad_component: dict) -> None:
    with pytest.raises(ValidationError):
        SemanticStoryboard.model_validate({
            "scenes": [
                {
                    "scene_number": 1,
                    "narration_text": "Giới thiệu về nội dung hôm nay.",
                    "purpose": "intro",
                    "components": [bad_component],
                }
            ],
            "total_duration_s": 30.0,
        })


def test_valid_semantic_storyboard_parses() -> None:
    tree = SemanticStoryboard.model_validate({
        "scenes": [
            {
                "scene_number": 1,
                "narration_text": "Giới thiệu về chủ đề hôm nay.",
                "narration_anchor": "giới thiệu",
                "purpose": "intro",
                "components": [
                    {"kind": "heading", "summary": "Tiêu đề", "content": {}},
                    {"kind": "body", "summary": "Nội dung", "content": {}},
                ],
            }
        ],
        "total_duration_s": 60.0,
    })
    assert len(tree.scenes) == 1
    assert tree.scenes[0].purpose == "intro"


def test_max_8_components_per_scene() -> None:
    scene_payload = {
        "scene_number": 1,
        "narration_text": "Nội dung dài với nhiều thành phầnUI.",
        "purpose": "explain",
        "components": [
            {"kind": "heading", "summary": f"Item {i}", "content": {}}
            for i in range(9)
        ],
    }
    with pytest.raises(ValidationError, match="at most 8"):
        SceneTreeScene.model_validate(scene_payload)


def test_bullet_max_6() -> None:
    """BR-6 enforces bullet ≤ 6 items."""
    scene_payload = {
        "scene_number": 1,
        "narration_text": "Danh sách bullet point dài.",
        "purpose": "data",
        "components": [
            {"kind": "bullet", "summary": f"Item {i}", "content": {"items": [f"t{i}"]}}
            for i in range(7)
        ],
    }
    with pytest.raises(ValidationError):
        SceneTreeScene.model_validate(scene_payload)


def test_scene_numbers_sequential() -> None:
    with pytest.raises(ValidationError, match="sequential"):
        SemanticStoryboard.model_validate({
            "scenes": [
                {"scene_number": 1, "narration_text": "Giới thiệu.", "purpose": "intro", "components": [VALID_COMPONENT]},
                {"scene_number": 3, "narration_text": "Giải thích.", "purpose": "explain", "components": [VALID_COMPONENT]},
            ],
            "total_duration_s": 60.0,
        })


def test_total_duration_within_range() -> None:
    payload = {
        "scenes": [
            {"scene_number": 1, "narration_text": "Giới thiệu.", "purpose": "intro", "components": [VALID_COMPONENT]},
        ],
        "total_duration_s": 0.0,
    }
    with pytest.raises(ValidationError, match="greater than 0"):
        SemanticStoryboard.model_validate(payload)
