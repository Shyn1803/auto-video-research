"""Semantic Storyboard (Scene Tree) — AI output schema, Step 1 of 4-6.

AI produces Scene Tree (content + intent only): component kinds, narration_anchor.
Nothing after Step 1 is an LLM call. Scene Tree is the ONLY input to the Layout Engine.
Any stray layout/position/font/animation/camera/transition field must fail loudly (BR-1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ComponentKind = Literal[
    "heading", "body", "media_intent", "stat", "bullet",
    "chart_data", "table_data", "quote", "code", "group",
]


class ComponentKindItem(BaseModel):
    """A semantic component inside a scene — no layout fields, ever."""

    model_config = ConfigDict(extra="forbid")

    kind: ComponentKind = Field(..., description="Semantic kind (10 kinds, snake_case)")
    summary: str = Field(
        min_length=1, max_length=500,
        description="One-line Vietnamese description of what this component conveys.",
    )
    narration_anchor: str | None = Field(
        default=None,
        description="Verbatim 20-80 char substring of narration_text that surfaces this component.",
    )
    content: dict = Field(
        default_factory=dict,
        description="Type-specific structured content per kind (stat.value, quote.text, etc.).",
    )
    media_query_vi: str | None = Field(
        default=None,
        description="Vietnamese description for media search (img/footage) — only for media_intent kind.",
    )
    media_hint: Literal["photo", "footage", "illustration"] | None = Field(
        default=None,
        description="Intended media type — only for media_intent kind.",
    )
    source_id: str | None = Field(
        default=None,
        description="Claim/source id backing this component (required for stat/chart data kinds).",
    )


class SceneTreeScene(BaseModel):
    """One scene in the semantic storyboard."""

    model_config = ConfigDict(extra="forbid")

    scene_number: int = Field(ge=1, le=99, description="Monotonic, 1-indexed order.")
    narration_text: str = Field(
        min_length=10, max_length=2000,
        description="Full voiceover script for this scene (must match write node's voice_over split).",
    )
    narration_anchor: str | None = Field(
        default=None,
        description="Optional scene-level anchor (verbatim substring of narration_text).",
    )
    purpose: Literal[
        "intro", "context", "explain", "evidence",
        "data", "comparison", "conclusion", "transition",
        "cta",
    ] = Field(description="Narrative purpose — drives Layout Classifier rule table.")
    components: list[ComponentKindItem] = Field(
        min_length=1, max_length=8,
        description="1-8 semantic components per scene. Never more.",
    )

    @field_validator("components")
    @classmethod
    def _validate_bullet_count(cls, v: list[ComponentKindItem]) -> list[ComponentKindItem]:
        bullets = [c for c in v if c.kind == "bullet"]
        if len(bullets) > 6:
            raise ValueError(f"bullet components exceed 6 (got {len(bullets)})")
        return v

    @field_validator("components")
    @classmethod
    def _validate_group_depth(cls, v: list[ComponentKindItem]) -> list[ComponentKindItem]:
        for c in v:
            if c.kind == "group" and c.content:
                depth = c.content.get("depth", 0)
                if depth > 2:
                    raise ValueError(f"group depth exceeds 2 (got {depth})")
        return v


class SemanticStoryboard(BaseModel):
    """AI produces a Semantic Storyboard — the input to the Layout Engine.

    No layout/position/font/animation/camera/transition fields allowed anywhere.
    Appearing in LLM output is a parse failure (BR-1), not a silent coercion.
    """

    model_config = ConfigDict(extra="forbid")

    scenes: list[SceneTreeScene] = Field(
        min_length=1, max_length=200,
        description="Ordered scene list. 60s target → typically 8-12 scenes.",
    )
    total_duration_s: float = Field(
        gt=0, le=600,
        description="AI-estimated total duration — used for scene count sanity check.",
    )

    @model_validator(mode="after")
    def _validate_no_layout_fields(self) -> SemanticStoryboard:
        """Guard: if any LLM output contains layout fields, this fails loudly."""
        layout_fields = {"layout", "position", "font", "animation", "camera", "transition"}
        raw = self.model_dump(mode="json")
        for scene in raw.get("scenes", []):
            for comp in scene.get("components", []):
                keys = set(comp.keys()) | set(comp.get("content", {}).keys())
                leaked = keys & layout_fields
                if leaked:
                    raise ValueError(
                        f"Layout field(s) {leaked} found in LLM output — "
                        "AI must not choose layout (BR-1). "
                        "Strip these fields from the storyboard.generate prompt output schema."
                    )
        return self

    @field_validator("scenes")
    @classmethod
    def _scene_numbers_sequential(cls, v: list[SceneTreeScene]) -> list[SceneTreeScene]:
        numbers = [s.scene_number for s in v]
        if numbers != list(range(1, len(v) + 1)):
            raise ValueError("scene_numbers must be sequential starting from 1")
        return v
