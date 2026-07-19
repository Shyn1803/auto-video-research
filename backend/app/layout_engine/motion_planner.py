"""Motion Planner pass-1 — Step 8 of 4-6 (BR-8, deterministic per layout-engine.md §9.2).

Produces a motion_plan (per-scene track list) that renders consume.
Rules:
- narration_anchor must be a verbatim substring of narration_text; otherwise
  drop the anchor and fall back to scene-sequence order, emit a warning.
- Attention budget: ≤1 large motion track simultaneously.
- Every track must declare a `reason`: narration_sync | hierarchy | sequence.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.scene_tree import SceneTreeScene

logger = logging.getLogger("avr.layout_engine.motion_planner")

VALID_REASONS = frozenset({"narration_sync", "hierarchy", "sequence"})


class _Track:
    """Internal representation before serialising to the contract's MotionTrack."""

    __slots__ = ("kind", "start_ms", "duration_ms", "reason", "anchor_used")

    def __init__(
        self, *, kind: str, start_ms: int, duration_ms: int, reason: str, anchor_used: bool
    ) -> None:
        if reason not in VALID_REASONS:
            raise ValueError(f"invalid motion reason={reason!r}; must be one of {VALID_REASONS}")
        self.kind = kind
        self.start_ms = start_ms
        self.duration_ms = duration_ms
        self.reason = reason
        self.anchor_used = anchor_used


def _anchor_offset(scene: SceneTreeScene, anchor: str | None) -> int | None:
    """Return character offset of anchor in scene.narration_text, or None."""
    if not anchor:
        return None
    try:
        return scene.narration_text.index(anchor)
    except ValueError:
        return None


def plan_scene(
    scene: SceneTreeScene,
    *,
    scene_start_ms: int,
    scene_duration_ms: int,
    prev_layout: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Produce motion tracks + warnings for a single scene.

    Returns (tracks, warnings). Each track dict has:
        kind, start_ms, duration_ms, reason, anchor_matched (bool).
    """
    warnings: list[str] = []
    tracks: list[_Track] = []
    ts = scene_start_ms

    # Determine if the scene has a valid anchor.
    anchor = scene.narration_anchor
    offset = _anchor_offset(scene, anchor) if anchor else None
    if anchor is not None and offset is None:
        warnings.append(
            f"scene {scene.scene_number}: narration_anchor not found in narration_text; "
            f"falling back to sequence order (no anchor-based motion)."
        )
        anchor = None  # fall back

    # Primary motion: entry track ("enter" / "fade_in" storytelling rule).
    # Heuristic: first 30% of scene duration for the dominant element entry.
    entry_dur = max(400, scene_duration_ms // 4)
    if anchor is not None:
        # Anchor-based: motion starts when narration reaches anchor position.
        # Rough char→ms ratio ≈ 8–12 cps for TTS Vietnamese. Use conservative 10 cps.
        anchor_ms = scene_start_ms + int(offset * 10)
        tracks.append(_Track(
            kind="fade_in",
            start_ms=anchor_ms,
            duration_ms=min(entry_dur, scene_start_ms + scene_duration_ms - anchor_ms),
            reason="narration_sync",
            anchor_used=True,
        ))
    else:
        # Sequence fallback: entry at scene start, hierarchy-based if layout changes.
        reason = "hierarchy" if prev_layout != scene.purpose else "sequence"
        tracks.append(_Track(
            kind="fade_in",
            start_ms=scene_start_ms,
            duration_ms=entry_dur,
            reason=reason,
            anchor_used=False,
        ))

    # Budget check: we only produce entry tracks at v1 (≤1 large motion).
    # Future: per-component in/out tracks for multi-element scenes.

    track_dicts = [
        {
            "kind": t.kind,
            "start_ms": t.start_ms,
            "duration_ms": t.duration_ms,
            "reason": t.reason,
            "anchor_matched": t.anchor_used,
        }
        for t in tracks
    ]
    return track_dicts, warnings


def plan_tree(
    classifications: list[dict[str, Any]],
    tree_scenes: list[SceneTreeScene],
    scene_duration_ms: int = 5000,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Produce motion_plan for all scenes in order.

    classifications: output of classify_tree().
    tree_scenes: original SemanticStoryboard.scenes (for narration_text/anchor).

    Returns (motion_plan_per_scene, all_warnings).
    """
    all_warnings: list[str] = []
    motion_plan: list[dict[str, Any]] = []
    t = 0
    prev_layout: str | None = None

    for cls, scene in zip(classifications, tree_scenes):
        tracks, warns = plan_scene(
            scene,
            scene_start_ms=t,
            scene_duration_ms=scene_duration_ms,
            prev_layout=prev_layout,
        )
        all_warnings.extend(warns)
        motion_plan.append({
            "scene_number": scene.scene_number,
            "layout": cls["layout"],
            "tracks": tracks,
        })
        t += scene_duration_ms
        prev_layout = cls["layout"]

    return motion_plan, all_warnings
