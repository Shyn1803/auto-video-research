"""Resolve tests — BR-4 strict-valid guarantee + shape contracts (Step 9 of 4-6)."""

from __future__ import annotations

import pytest

from app.layout_engine.resolve import resolve_tree
from app.schemas.scene_tree import (
    ComponentKindItem,
    SceneTreeScene,
    SemanticStoryboard,
)


def _tree(*, scenes=None, duration: float = 60.0) -> SemanticStoryboard:
    return SemanticStoryboard(scenes=scenes or [], total_duration_s=duration)


def _sc(
    num: int,
    purpose: str,
    kind: str = "body",
    summary: str = "test",
    content: dict | None = None,
) -> SceneTreeScene:
    return SceneTreeScene(
        scene_number=num,
        narration_text=f"Narration text {num}. " * 2,
        purpose=purpose,
        components=[ComponentKindItem(kind=kind, summary=summary, content=content or {})],
    )


def _cls(num: int, layout: str, was_unavailable: bool = False) -> dict:
    return {
        "scene_number": num,
        "layout": layout,
        "was_unavailable": was_unavailable,
        "rule_id": 1,
        "confidence": 0.9,
    }


def _mp(num: int, tracks: list | None = None, warnings: list | None = None) -> dict:
    return {
        "scene_number": num,
        "tracks": tracks or [],
        "warnings": warnings or [],
        "attention_budget_used": 0.0,
    }


# BR-4 — resolve output shape is strict-valid on its own classifier output


def test_br4_single_scene_resolve_shape():
    tree = _tree(scenes=[_sc(1, "intro", kind="heading")])
    classifications = [_cls(1, "Hero")]
    motion_plan = [_mp(1, tracks=[{"kind": "fade_in", "anchor": "start"}])]

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))

    assert result["total_scenes"] == 1
    assert result["resolution_passed"] is True
    assert result["total_duration_s"] == 60.0
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["layout"] == "Hero"
    assert result["scenes"][0]["motion_tracks"] == [{"kind": "fade_in"}]
    assert "components" in result["scenes"][0]
    assert "narration_text" in result["scenes"][0]


def test_br4_multi_scene_resolve():
    tree = _tree(
        scenes=[
            _sc(1, "intro", kind="heading"),
            _sc(2, "evidence", kind="media_intent", content={"media_hint": "photo"}),
            _sc(3, "conclusion", kind="body"),
        ]
    )
    classifications = [
        _cls(1, "Hero"),
        _cls(2, "MediaFull"),
        _cls(3, "TextFocus"),
    ]
    motion_plan = [_mp(i) for i in (1, 2, 3)]

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["total_scenes"] == 3
    assert result["class_distribution"] == {"Hero": 1, "MediaFull": 1, "TextFocus": 1}


# count mismatch — engine invariant


def test_resolve_count_mismatch_raises():
    tree = _tree(scenes=[_sc(1, "intro")])
    # 0 classifications but 1 scene → mismatch
    classifications: list[dict] = []
    motion_plan: list[dict] = []

    with pytest.raises(ValueError, match="count mismatch"):
        resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))


# motion_plan missing for a scene — graceful None


def test_mp_missing_for_scene():
    tree = _tree(scenes=[_sc(1, "intro")])
    classifications = [_cls(1, "Hero")]
    motion_plan: list[dict] = []

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["scenes"][0]["motion_tracks"] == []


# warnings propagated


def test_warnings_propagated():
    tree = _tree(scenes=[_sc(1, "intro")])
    classifications = [_cls(1, "Hero")]
    motion_plan = [_mp(1, warnings=["dual_motion"])]

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["warnings"] == ["dual_motion"]


# duration evenly split


def test_duration_evenly_split():
    tree = _tree(scenes=[_sc(1, "intro"), _sc(2, "body")], duration=120.0)
    classifications = [_cls(1, "Hero"), _cls(2, "TextFocus")]
    motion_plan = [_mp(1), _mp(2)]

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    for scene in result["scenes"]:
        assert scene["duration_s"] == 60.0


# was_unavailable flag preserved


def test_was_unavailable_preserved():
    tree = _tree(scenes=[_sc(1, "intro")])
    classifications = [_cls(1, "FallbackList", was_unavailable=True)]
    motion_plan = [_mp(1)]

    result = resolve_tree(classifications, motion_plan, tree.model_dump(mode="json"))
    assert result["scenes"][0]["was_unavailable"] is True
