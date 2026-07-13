"""Shared Scene JSON fixture contract tests."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.scene import Scene
from app.services.scene_validator import SceneValidationError, validate_scene

FIXTURES = Path(__file__).resolve().parents[4] / "packages/remotion-templates/schema/fixtures"


def load_fixture(name: str) -> dict[str, object]:
    """Load a shared JSON contract fixture."""

    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.valid.json")))
def test_valid_scene_fixtures_parse_in_pydantic(fixture: Path) -> None:
    """Every valid shared fixture parses and satisfies strict layout constraints."""

    scene = Scene.model_validate_json(fixture.read_text())

    assert validate_scene(scene, "strict") == scene


def test_duration_type_fixture_fails_in_pydantic() -> None:
    """The shared wrong-type fixture reports the duration field."""

    with pytest.raises(ValidationError) as error:
        Scene.model_validate(load_fixture("duration-type.invalid.json"))

    assert "duration_ms" in str(error.value)


def test_text_focus_overflow_fixture_fails_strictly() -> None:
    """The shared overflow fixture maps to the editor field path."""

    scene = Scene.model_validate(load_fixture("text-focus-overflow.invalid.json"))

    with pytest.raises(SceneValidationError, match="texts") as error:
        validate_scene(scene, "strict")

    assert error.value.field_path == "texts"


def test_missing_required_fixture_fails_in_pydantic() -> None:
    """The shared missing-field fixture is rejected by the base schema."""

    with pytest.raises(ValidationError) as error:
        Scene.model_validate(load_fixture("missing-scene-id.invalid.json"))

    assert "scene_id" in str(error.value)
