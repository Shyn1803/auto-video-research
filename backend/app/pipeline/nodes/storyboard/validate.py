"""Storyboard validation — Step 2 (BR-2) + Step 6 (BR-6) of 4-6.

BR-2: concatenated per-scene narration_text must equal voice_over (normalised).
BR-6: data-kind components missing source_id — strict block or auto-downgrade.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from app.schemas.scene_tree import ComponentKindItem, SceneTreeScene

logger = logging.getLogger("avr.storyboard.validate")

DATA_KINDS = frozenset({"stat", "chart_data", "table_data", "quote"})

VALID_REASONS = frozenset({"narration_sync", "hierarchy", "sequence"})


# ———— BR-2 helpers ————

_NORMALISE_RE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _NORMALISE_RE.sub(" ", unicodedata.normalize("NFC", text).strip().lower())


def validate_narration_matches_voiceover(
    scenes: list[SceneTreeScene],
    voice_over: str,
    *,
    strict: bool = True,
) -> list[str]:
    """Return validation errors (empty = pass).

    BR-2: concatenated narration_text (normalised) must equal voice_over (normalised).
    Per BR-2, any mismatch is an engine bug — never ship with a warning.
    """
    errors: list[str] = []
    concat = _normalise(" ".join(s.narration_text for s in scenes))
    expected = _normalise(voice_over)
    if concat != expected:
        errors.append(
            f"BR-2: narration concat mismatch "
            f"(got {len(concat)} chars, expected {len(expected)} chars)"
        )
        if not strict:
            logger.warning("narration mismatch: len(got)=%d len(expected)=%d", len(concat), len(expected))
    return errors


# ———— BR-6 helpers ————

def validate_component_source_ids(
    scenes: list[SceneTreeScene],
    *,
    strict: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (errors, auto_fixes).

    strict=True  → missing source_id on data-kind is a hard block (error).
    strict=False → auto-downgrade to body with a warning (fix).
    """
    errors: list[str] = []
    fixes: list[dict[str, Any]] = []

    for scene in scenes:
        for comp in scene.components:
            if comp.kind not in DATA_KINDS:
                continue
            if comp.source_id:
                continue
            msg = (
                f"scene {scene.scene_number}: {comp.kind} component "
                f"(summary={comp.summary!r}) missing source_id"
            )
            if strict:
                errors.append(f"BR-6 strict block: {msg}")
            else:
                fixes.append(
                    {
                        "scene_number": scene.scene_number,
                        "component_index": scene.components.index(comp),
                        "from_kind": comp.kind,
                        "to_kind": "body",
                        "reason": "missing source_id",
                    }
                )
                logger.warning("BR-6 auto_fix: %s → body", msg)

    return errors, fixes


# ———— validate_tree (combined) ————

def validate_tree(
    scenes: list[SceneTreeScene],
    voice_over: str,
    *,
    strict_source_id: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Run all semantic-tree validations.

    Returns (hard_errors, auto_fixes). Hard errors block the pipeline (BR-2/BR-6
    strict). Auto fixes (BR-6 lenient) are applied downstream before resolve.
    """
    errors = validate_narration_matches_voiceover(scenes, voice_over, strict=True)
    _, fixes = validate_component_source_ids(scenes, strict=strict_source_id)
    return errors, fixes
