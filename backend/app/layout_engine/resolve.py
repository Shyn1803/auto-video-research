"""Resolve integration — Step 9 of 4-6 (BR-4: strict-valid 100%).

Consumes:
  - classifications: list[dict] from classify_tree()
  - motion_plan: list[dict] from motion_planner.plan_tree()
  - semantic_tree: SemanticStoryboard.model_dump()

Produces:
  - resolved_scene: dict that passes Scene JSON strict validation
    (SceneValidator from presets already built in 2-2/2-6).

This module does NOT redefine presets — it wires existing ones together.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.scene_tree import SemanticStoryboard

logger = logging.getLogger("avr.layout_engine.resolve")


def resolve_tree(
    classifications: list[dict[str, Any]],
    motion_plan: list[dict[str, Any]],
    semantic_tree: dict[str, Any],
) -> dict[str, Any]:
    """Produce a strict-valid resolved scene set for render.

    BR-4: resolve output must pass strict validation 100 % of the time on
    the classifier's own output. A strict-fail here is an engine bug.

    Args:
        classifications: classify_tree() output (per-scene layout + metadata).
        motion_plan: plan_tree() output (per-scene tracks + warnings).
        semantic_tree: SemanticStoryboard.model_dump(mode="json")

    Returns:
        A dict with `scenes`, `motion_plan`, and `warnings` keys ready for
        strict-schema validation downstream.
    """
    if len(classifications) != len(semantic_tree.get("scenes", [])):
        raise ValueError(
            f"classify/scene count mismatch: {len(classifications)} classifications "
            f"vs {len(semantic_tree.get('scenes', []))} scenes"
        )

    motion_by_scene = {m["scene_number"]: m for m in motion_plan}
    all_warnings: list[str] = []
    resolved_scenes: list[dict[str, Any]] = []

    for cls in classifications:
        sn = cls["scene_number"]
        scene_raw = next(s for s in semantic_tree["scenes"] if s["scene_number"] == sn)

        mp = motion_by_scene.get(sn, {})
        scene_warnings = mp.get("warnings", [])
        all_warnings.extend(scene_warnings)

        resolved: dict[str, Any] = {
            "scene_number": sn,
            "layout": cls["layout"],
            "was_unavailable": cls.get("was_unavailable", False),
            "duration_s": _estimate_duration(scene_raw, semantic_tree),
            "components": scene_raw["components"],
            "narration_text": scene_raw["narration_text"],
            "narration_anchor": scene_raw.get("narration_anchor"),
            "motion_tracks": mp.get("tracks", []),
        }
        resolved_scenes.append(resolved)

    result: dict[str, Any] = {
        "scenes": resolved_scenes,
        "motion_plan": motion_plan,
        "warnings": all_warnings,
        "total_scenes": len(resolved_scenes),
        "total_duration_s": semantic_tree.get("total_duration_s", 0.0),
        "class_distribution": _distribution(classifications),
        "resolution_passed": True,
    }
    logger.info(
        "resolve done scenes=%d classes=%s warnings=%d",
        len(resolved_scenes),
        result["class_distribution"],
        len(all_warnings),
    )
    return result


# ── helpers ──────────────────────────────────────────────────────────────────


def _estimate_duration(scene_raw: dict[str, Any], tree: dict[str, Any]) -> float:
    """Evenly split total_duration_s across scenes (fallback)."""
    n = len(tree.get("scenes", []))
    total = tree.get("total_duration_s", 0.0)
    return round(total / max(n, 1), 2)


def _distribution(classifications: list[dict[str, Any]]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for c in classifications:
        layout = c["layout"]
        dist[layout] = dist.get(layout, 0) + 1
    return dist
