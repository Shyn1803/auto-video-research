"""Semantic Analysis — Step 3 of 4-6 (pass 1: pure function, no LLM).

Computes a deterministic content profile from the Scene Tree that the
Layout Classifier consumes. Same tree → same profile every time (BR-3).
"""

from __future__ import annotations

import logging
from collections import Counter

from app.schemas.scene_tree import ComponentKindItem, SemanticStoryboard

logger = logging.getLogger("avr.layout_engine.analysis")

COMPONENT_KINDS = {
    "heading", "body", "media_intent", "stat", "bullet",
    "chart_data", "table_data", "quote", "code", "group",
}

DATA_KINDS = {"stat", "chart_data", "table_data", "quote"}


class SceneProfile:
    """Per-scene content profile."""

    __slots__ = (
        "scene_number",
        "purpose",
        "total_components",
        "kind_counts",
        "dominant_kind",
        "density",
        "has_data",
        "has_media",
        "has_code",
        "narration_length_chars",
    )

    def __init__(
        self,
        scene_number: int,
        purpose: str,
        total_components: int,
        kind_counts: dict[str, int],
        dominant_kind: str,
        density: str,
        has_data: bool,
        has_media: bool,
        has_code: bool,
        narration_length_chars: int,
    ) -> None:
        self.scene_number = scene_number
        self.purpose = purpose
        self.total_components = total_components
        self.kind_counts = kind_counts
        self.dominant_kind = dominant_kind
        self.density = density
        self.has_data = has_data
        self.has_media = has_media
        self.has_code = has_code
        self.narration_length_chars = narration_length_chars


class VideoProfile:
    """Aggregate profile across all scenes."""

    __slots__ = (
        "total_scenes",
        "total_duration_s",
        "class_distribution",
        "primary_purpose",
        "has_data_scenes",
        "has_code_scenes",
        "dominant_kind",
    )

    def __init__(
        self,
        total_scenes: int,
        total_duration_s: float,
        class_distribution: dict[str, int],
        primary_purpose: str,
        has_data_scenes: bool,
        has_code_scenes: bool,
        dominant_kind: str,
    ) -> None:
        self.total_scenes = total_scenes
        self.total_duration_s = total_duration_s
        self.class_distribution = class_distribution
        self.primary_purpose = primary_purpose
        self.has_data_scenes = has_data_scenes
        self.has_code_scenes = has_code_scenes
        self.dominant_kind = dominant_kind


def _density_label(comp_count: int, narration_chars: int) -> str:
    """Coarse density bucket used by the rule table."""
    if narration_chars < 100 and comp_count <= 2:
        return "light"
    if narration_chars < 300 and comp_count <= 4:
        return "medium"
    return "heavy"


def analyze_scene(scene: SceneTreeScene) -> SceneProfile:
    """Produce a scene-level content profile from a single SceneTreeScene."""
    counts: Counter[str] = Counter()
    for comp in scene.components:
        if comp.kind in COMPONENT_KINDS:
            counts[comp.kind] += 1
        else:
            logger.warning("unknown component kind=%r scene=%d", comp.kind, scene.scene_number)

    dominant = counts.most_common(1)
    dominant_kind = dominant[0][0] if dominant else "body"

    return SceneProfile(
        scene_number=scene.scene_number,
        purpose=scene.purpose,
        total_components=len(scene.components),
        kind_counts=dict(counts),
        dominant_kind=dominant_kind,
        density=_density_label(len(scene.components), len(scene.narration_text)),
        has_data=any(c.kind in DATA_KINDS for c in scene.components),
        has_media=any(c.kind == "media_intent" for c in scene.components),
        has_code=any(c.kind == "code" for c in scene.components),
        narration_length_chars=len(scene.narration_text),
    )


def analyze_tree(tree: SemanticStoryboard) -> VideoProfile:
    """Produce a deterministic video-level profile from the full Scene Tree.

    Same input tree always produces the same output (BR-3).
    """
    scene_profiles = [analyze_scene(s) for s in tree.scenes]

    distribution: Counter[str] = Counter()
    purposes: Counter[str] = Counter()
    for sp in scene_profiles:
        distribution[sp.dominant_kind] += 1
        purposes[sp.purpose] += 1

    primary_purpose = purposes.most_common(1)[0][0] if purposes else "explain"
    dominant_kind = distribution.most_common(1)[0][0] if distribution else "body"

    return VideoProfile(
        total_scenes=len(tree.scenes),
        total_duration_s=tree.total_duration_s,
        class_distribution=dict(distribution),
        primary_purpose=primary_purpose,
        has_data_scenes=any(sp.has_data for sp in scene_profiles),
        has_code_scenes=any(sp.has_code for sp in scene_profiles),
        dominant_kind=dominant_kind,
    )
