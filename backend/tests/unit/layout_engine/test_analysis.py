"""Tests for layout_engine/analysis.py — Step 3+4 of 4-6.

Covers: deterministic output (BR-3), dominant-kind detection, density classification.
"""
from __future__ import annotations

import pytest

from app.layout_engine.analysis import (
    SceneProfile,
    VideoProfile,
    analyze_scene,
    analyze_tree,
)
from app.schemas.scene_tree import (
    ComponentKindItem,
    SceneTreeScene,
    SemanticStoryboard,
)


def _scene(text: str, purpose: str, *, num: int) -> SceneTreeScene:
    comps = [ComponentKindItem(kind="body", summary="body", content={})]
    return SceneTreeScene(
        scene_number=num, narration_text=text, purpose=purpose, components=comps
    )


def _tree(scenes: list[SceneTreeScene], duration: float = 60.0) -> SemanticStoryboard:
    return SemanticStoryboard(scenes=scenes, total_duration_s=duration)


class TestAnalyzeScene:
    def test_dominant_kind_single(self) -> None:
        comps = [
            ComponentKindItem(kind="heading", summary="t", content={}),
            ComponentKindItem(kind="heading", summary="t2", content={}),
            ComponentKindItem(kind="body", summary="b", content={}),
        ]
        scene = SceneTreeScene(
            scene_number=1,
            narration_text="Tieu de truy cap nguoi dung va thong bao chao.",
            purpose="intro",
            components=comps,
        )
        prof = analyze_scene(scene)
        assert prof.dominant_kind == "heading"
        assert prof.total_components == 3

    def test_has_data_true(self) -> None:
        comps = [
            ComponentKindItem(kind="stat", summary="123", content={"value": 123}, source_id="c1"),
        ]
        scene = SceneTreeScene(
            scene_number=1,
            narration_text="Con so dang chu y hom nay trong bao cao.",
            purpose="data",
            components=comps,
        )
        prof = analyze_scene(scene)
        assert prof.has_data is True
        assert prof.has_media is False

    def test_density_light(self) -> None:
        comps = [ComponentKindItem(kind="heading", summary="t", content={})]
        scene = SceneTreeScene(
            scene_number=1,
            narration_text="Gioi thieu ngan gon van ban.",
            purpose="intro",
            components=comps,
        )
        assert analyze_scene(scene).density == "light"

    def test_density_heavy(self) -> None:
        # 35 chars * 50 = 1750, stays under max_length=2000
        long_text = "Noi dung chi tiet phan tich tai chinh. " * 50
        comps = [ComponentKindItem(kind="body", summary="t", content={}) for _ in range(8)]
        scene = SceneTreeScene(
            scene_number=1,
            narration_text=long_text,
            purpose="explain",
            components=comps,
        )
        assert analyze_scene(scene).density == "heavy"


class TestAnalyzeTree:
    def test_deterministic_br3(self) -> None:
        """Same tree -> identical profile (BR-3)."""
        s1 = _scene("Mo dau gioi thieu chu de chinh.", "intro", num=1)
        s2 = _scene("Giai thich chi tiet noi dung phan tich.", "explain", num=2)
        tree = _tree([s1, s2])
        profile_a = analyze_tree(tree)
        profile_b = analyze_tree(tree)
        assert {s: getattr(profile_a, s) for s in VideoProfile.__slots__} == {s: getattr(profile_b, s) for s in VideoProfile.__slots__}

    def test_class_distribution(self) -> None:
        comps_h = [ComponentKindItem(kind="heading", summary="h", content={})]
        comps_b = [ComponentKindItem(kind="body", summary="b", content={})]
        scenes = [
            SceneTreeScene(scene_number=1, narration_text="Gioi thieu khai quat ve chu de.", purpose="intro", components=comps_h),
            SceneTreeScene(scene_number=2, narration_text="Giai thich chi tiet noi dung phan tich.", purpose="explain", components=comps_b),
            SceneTreeScene(scene_number=3, narration_text="Bo cuc lich su va xu huong hien tai.", purpose="context", components=comps_h),
        ]
        tree = _tree(scenes)
        prof = analyze_tree(tree)
        assert prof.total_scenes == 3
        assert prof.class_distribution.get("heading") == 2
