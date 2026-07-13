"""Semantic validation and safe normalization for resolved Scene JSON."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Literal

from app.schemas.scene import Scene

logger = logging.getLogger(__name__)

ValidationMode = Literal["auto_fix", "strict"]


class SceneValidationError(ValueError):
    """A validation failure with a frontend-addressable field path."""

    def __init__(self, field_path: str, message: str) -> None:
        super().__init__(message)
        self.field_path = field_path


LAYOUT_LIMITS: dict[str, tuple[range, range]] = {
    # Original 5 layout classes
    "Hero": (range(1, 3), range(0, 2)),
    "TextFocus": (range(1, 4), range(0, 1)),
    "MediaFull": (range(0, 3), range(1, 2)),
    "MediaText": (range(1, 4), range(1, 2)),
    "Comparison": (range(0, 4), range(2, 3)),
    # 6 new layout classes added in 10-2
    "BigNumber": (range(1, 3), range(0, 2)),    # stat + optional body
    "Chart": (range(1, 4), range(0, 1)),         # heading + chart + optional body
    "VersusTable": (range(1, 3), range(0, 1)),   # heading + table_data
    "List": (range(1, 3), range(0, 1)),          # heading + bullet (bullet is text)
    "Quote": (range(1, 3), range(0, 1)),         # quote + body (both text)
    "Code": (range(1, 3), range(0, 1)),          # heading + code (code is text)
}


def _validate_count(
    payload: dict[str, object], field_path: str, allowed: range, mode: ValidationMode
) -> None:
    """Enforce a layout cardinality, trimming only excess safe values in auto-fix mode."""

    elements = payload[field_path]
    assert isinstance(elements, list)
    if len(elements) in allowed:
        return
    if len(elements) > max(allowed) and mode == "auto_fix":
        payload[field_path] = elements[: max(allowed)]
        logger.warning("scene_validator_trimmed", extra={"field_path": field_path})
        return
    raise SceneValidationError(field_path, f"{field_path} count is incompatible with layout")


def validate_scene(scene: Scene, mode: ValidationMode = "strict") -> Scene:
    """Validate a resolved scene, returning an optionally safe-normalized copy."""

    payload = deepcopy(scene.model_dump(mode="python"))
    limits = LAYOUT_LIMITS.get(scene.layout)
    if limits is not None:
        text_range, image_range = limits
        _validate_count(payload, "texts", text_range, mode)
        _validate_count(payload, "images", image_range, mode)

    voice = scene.voice
    if voice is not None and voice.audio is not None:
        required_duration = voice.audio.duration_ms + 300
        if scene.duration_ms < required_duration:
            if mode == "auto_fix":
                payload["duration_ms"] = required_duration
                logger.warning(
                    "scene_validator_extended_duration", extra={"field_path": "duration_ms"}
                )
            else:
                raise SceneValidationError("duration_ms", "duration must include voice padding")

    for field_path in ("texts", "images"):
        elements = payload[field_path]
        assert isinstance(elements, list)
        for element in elements:
            assert isinstance(element, dict)
            animation = element.get("animation")
            if animation is None:
                continue
            assert isinstance(animation, dict)
            if animation["delay_ms"] + animation["duration_ms"] > payload["duration_ms"]:
                raise SceneValidationError(field_path, "animation extends beyond scene duration")

    return Scene.model_validate(payload)
