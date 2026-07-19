"""Layout Classifier — Step 4 of 4-6 (deterministic rule table, config-driven).

Rule table versioned so rule changes don't require a deploy. Rule table format:
one rule per row, matched in order — first match wins. Fallback table for the
"class not available" case (BR-7).

Layout class names are PascalCase canonical: Hero, TextFocus, MediaFull,
MediaText, Comparison, BigNumber, Chart, VersusTable, List, Quote, Code.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml  # pyyaml — available in deps

from app.layout_engine.analysis import analyze_tree, analyze_scene, SceneProfile, VideoProfile

logger = logging.getLogger("avr.layout_engine.classifier")

# Starter rule table (12 rules per Decisions locked). In production this is
# loaded from app/layout_engine/classifier_rules.yaml.
_STARTER_RULES = [
    # (purpose, density, has_data, has_media, has_code, min_duration_s, layout)
    ("intro",     "light",  False, False, False, 0,  "Hero"),
    ("intro",     "medium", False, False, False, 0,  "TextFocus"),
    ("context",   "light",  False, False, False, 0,  "TextFocus"),
    ("context",   "medium", False, False, False, 0,  "TextFocus"),
    ("explain",   "light",  False, False, False, 0,  "TextFocus"),
    ("explain",   "medium", False, False, False, 0,  "TextFocus"),
    ("explain",   "heavy",  False, False, False, 0,  "TextFocus"),
    ("evidence",  "medium", False, True,  False, 0,  "MediaText"),
    ("evidence",  "heavy",  False, True,  False, 0,  "MediaFull"),
    ("evidence",  "medium", True,  False, False, 0,  "Quote"),
    ("data",      "light",  True,  False, False, 0,  "BigNumber"),
    ("data",      "medium", True,  False, False, 0,  "Chart"),
    ("data",      "heavy",  True,  False, False, 0,  "VersusTable"),
    ("comparison","light",  False, True,  False, 0,  "Comparison"),
    ("comparison","medium", False, True,  False, 0,  "Comparison"),
    ("comparison","heavy",  False, True,  False, 0,  "MediaFull"),
    ("conclusion","light",  False, False, False, 0,  "Hero"),
    ("conclusion","medium", False, False, False, 0,  "TextFocus"),
    ("cta",       "light",  False, False, False, 0,  "Hero"),
    ("transition","light",  False, False, False, 0,  "TextFocus"),
    # Code-specific
    ("explain",   "medium", False, False, True,  0,  "Code"),
    ("data",      "light",  False, False, True,  0,  "Code"),
    # Fallbacks when has_media=True but rule missed
    ("data",      "medium", False, True,  False, 0,  "List"),
    ("data",      "heavy",  False, True,  False, 0,  "VersusTable"),
]

# Fallbacks when a matched layout is unavailable in the format/template set.
FALLBACK_TABLE: dict[str, str] = {
    "Gallery":    "MediaText",
    "VersusTable": "Comparison",
    "Code":       "TextFocus",
    "BigNumber":  "Chart",
    "Chart":      "List",
}

# v1 unavailable classes (per Decisions locked).
_UNAVAILABLE_V1: set[str] = {"Gallery"}


def _load_rules() -> list[dict[str, Any]]:
    """Load rule table from YAML or fall back to starter rules."""
    rules_path = Path(__file__).parent / "classifier_rules.yaml"
    if rules_path.exists():
        try:
            data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
            return data.get("rules", _STARTER_RULES)  # type: ignore[return-value]
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to load classifier_rules.yaml: %s; using starter rules", exc)
    return _STARTER_RULES


def _match_rule(
    profile: SceneProfile, rules: list[dict[str, Any]], unavailable: set[str]
) -> tuple[str, bool]:
    """Return (layout, was_unavailable)."""
    for rule in rules:
        if (
            rule["purpose"] == profile.purpose
            and rule["density"] == profile.density
            and rule["has_data"] == profile.has_data
            and rule["has_media"] == profile.has_media
            and rule["has_code"] == profile.has_code
            and profile.narration_length_chars >= rule.get("min_duration_s", 0) * 1000
        ):
            layout = rule["layout"]
            if layout in unavailable:
                fallback = FALLBACK_TABLE.get(layout, "TextFocus")
                logger.warning("layout=%s unavailable v1; falling back to %s scene=%d", layout, fallback, profile.scene_number)
                return fallback, True
            return layout, False
    # No rule matched → TextFocus default (always available).
    return "TextFocus", False


def classify_scene(
    scene_num: int,
    profile: SceneProfile,
    rules: list[dict[str, Any]] | None = None,
    unavailable: set[str] | None = None,
) -> str:
    """Return a layout class for a single scene (deterministic, BR-3)."""
    if rules is None:
        rules = _STARTER_RULES  # type: ignore[assignment]
    if unavailable is None:
        unavailable = _UNAVAILABLE_V1
    layout, _ = _match_rule(profile, rules, unavailable)
    return layout


def classify_tree(
    tree: SemanticStoryboard,
    *,
    layout_override: dict[int, str] | None = None,
    unavailable: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Produce scene classifications for all scenes in the tree.

    Returns one dict per scene:
        {"scene_number": int, "layout": str, "was_unavailable": bool, "profile": SceneProfile.__dict__}

    layout_override keyed by scene_number wins over classifier choice (BR-5).
    """
    if unavailable is None:
        unavailable = _UNAVAILABLE_V1

    rules = _load_rules()
    video = analyze_tree(tree)
    results: list[dict[str, Any]] = []

    for scene in tree.scenes:
        profile = analyze_scene(scene)
        layout, was_unavail = _match_rule(profile, rules, unavailable)

        override = (layout_override or {}).get(scene.scene_number)
        if override is not None:
            layout = override
            logger.debug("layout override scene=%d → %s", scene.scene_number, layout)

        results.append({
            "scene_number": scene.scene_number,
            "layout": layout,
            "was_unavailable": was_unavail,
            "profile": {
                "scene_number": profile.scene_number,
                "purpose": profile.purpose,
                "density": profile.density,
                "dominant_kind": profile.dominant_kind,
                "has_data": profile.has_data,
                "has_media": profile.has_media,
                "has_code": profile.has_code,
            },
        })

    logger.info(
        "classify done scenes=%d distribution=%s dominant=%s",
        len(results),
        {r["layout"]: sum(1 for x in results if x["layout"] == r["layout"]) for r in results},
        video.dominant_kind,
    )
    return results
