"""Scene JSON semantic-validator and LLM-boundary tests."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.scene import Scene, SemanticStoryboard
from app.services.scene_validator import SceneValidationError, validate_scene

FIXTURES = Path(__file__).resolve().parents[4] / "packages/remotion-templates/schema/fixtures"


def load_scene(name: str) -> Scene:
    """Create a Pydantic Scene from the shared fixture directory."""

    return Scene.model_validate(json.loads((FIXTURES / name).read_text()))


def test_auto_fix_trims_text_focus_and_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """AC-2: safe excess text is trimmed and announces its correction."""

    fixed = validate_scene(load_scene("text-focus-overflow.invalid.json"), "auto_fix")

    assert len(fixed.texts) == 3
    assert any(record.message == "scene_validator_trimmed" for record in caplog.records)


def test_strict_text_focus_overflow_maps_to_texts() -> None:
    """AC-2: editor saves receive a machine-readable texts path."""

    with pytest.raises(SceneValidationError) as error:
        validate_scene(load_scene("text-focus-overflow.invalid.json"), "strict")

    assert error.value.field_path == "texts"


def test_duration_type_is_rejected_before_auto_fix() -> None:
    """AC-4: wrong primitive types are never silently repaired."""

    payload = json.loads((FIXTURES / "duration-type.invalid.json").read_text())

    with pytest.raises(ValidationError) as error:
        Scene.model_validate(payload)

    assert "duration_ms" in str(error.value)


@pytest.mark.parametrize("forbidden", ["layout", "position", "font", "animation", "camera"])
def test_semantic_storyboard_rejects_layout_instructions(forbidden: str) -> None:
    """AI output cannot cross the deterministic layout-engine boundary."""

    payload = {
        "scenes": [
            {
                "purpose": "hook",
                "narration": "Mở đầu",
                "components": [{"kind": "heading", "text": "Tiêu đề"}],
                forbidden: "forbidden-value",
            }
        ]
    }

    with pytest.raises(ValidationError):
        SemanticStoryboard.model_validate(payload)
