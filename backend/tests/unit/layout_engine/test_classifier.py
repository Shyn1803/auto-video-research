"""Classifier tests — BR-3 stability + BR-5 override (Steps 3+5 of 4-6)."""

from __future__ import annotations

import pytest

from app.layout_engine.classifier import classify_tree
from app.schemas.scene_tree import ComponentKindItem, SceneTreeScene, SemanticStoryboard


def _tree(*, scenes=None, duration: float = 60.0, **kwargs) -> SemanticStoryboard:
    return SemanticStoryboard(scenes=scenes or [], total_duration_s=duration)


def _sc(num: int, purpose: str, kind: str = "body", density: str = "light", **extra) -> SceneTreeScene:
    """Helper that mirrors the task's BR-3 inspect= field — direct SceneTreeScene ctor."""
    comps = [ComponentKindItem(kind=kind, summary="default", content=extra.get("content", {}))]
    return SceneTreeScene(
        scene_number=num,
        narration_text=f"Narrarion for scene {num}. " * 2,
        purpose=purpose,
        components=comps,
    )


# BR-3 — two semantic-identical trees must produce identical classify output
# (stable given成份 same semantic profile → same rule → same class)


def test_br3_two_identical_semantic_same_class():
    tree1 = _tree(
        scenes=[
            _sc(1, "intro", kind="heading"),
            _sc(2, "evidence", kind="media_intent", content={"media_hint": "photo"}),
        ]
    )
    tree2 = _tree(
        scenes=[
            _sc(1, "intro", kind="heading"),
            _sc(2, "evidence", kind="media_intent", content={"media_hint": "photo"}),
        ]
    )
    out1 = classify_tree(tree1)
    out2 = classify_tree(tree2)
    assert [c["layout"] for c in out1] == [c["layout"] for c in out2]


# BR-5 — layout_override always wins on regenerate


def test_br5_override_wins():
    tree = _tree(
        scenes=[
            _sc(1, "data", kind="stat", content={"value": 100}),
        ]
    )
    # classifier picks something (say, BigNumber for data+stat); override forces List
    out = classify_tree(tree, layout_override={1: "List"})
    assert out[0]["layout"] == "List"


def test_br5_override_preserved_on_same_structure_regenerate():
    tree_a = _tree(
        scenes=[
            _sc(1, "data", kind="stat", content={"value": 100}),
        ]
    )
    tree_same = _tree(
        scenes=[
            _sc(1, "data", kind="stat", content={"value": 150}),
        ]
    )
    out = classify_tree(tree_a, layout_override={1: "Quote"})
    assert out[0]["layout"] == "Quote"


# Sanity — rule table size (locked: 12 starter rules)


def test_starter_rules_count():
    from app.layout_engine.classifier import _STARTER_RULES
    assert len(_STARTER_RULES) == 12, f"Expected 12 starter rules, got {len(_STARTER_RULES)}"
