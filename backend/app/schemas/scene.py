"""The versioned Scene JSON render contract and strict AI storyboard input."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

LayoutName = Literal[
    "Hero",
    "TextFocus",
    "MediaFull",
    "MediaText",
    "Comparison",
    "BigNumber",
    "Chart",
    "VersusTable",
    "List",
    "Quote",
    "Code",
]
Format = Literal["vertical_1080x1920", "horizontal_1920x1080"]
PlatformProfile = Literal["generic", "tiktok", "facebook_reels", "youtube_shorts", "youtube_video"]


class ContractModel(BaseModel):
    """Base model that rejects undeclared render-contract fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class AssetRef(ContractModel):
    """A licensed internal asset or a temporary allowlisted source URL."""

    asset_id: str | None = None
    url: HttpUrl | None = None


class ColorBackground(ContractModel):
    """A solid-color background."""

    type: Literal["color"]
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class GradientBackground(ContractModel):
    """A linear-gradient background."""

    type: Literal["gradient"]
    from_: str = Field(alias="from", pattern=r"^#[0-9A-Fa-f]{6}$")
    to: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    angle: int = Field(default=180, ge=0, le=360)


class ImageBackground(ContractModel):
    """An image background with a readability overlay."""

    type: Literal["image"]
    asset: AssetRef
    overlay_opacity: float = Field(default=0.4, ge=0, le=1)


Background = Annotated[
    ColorBackground | GradientBackground | ImageBackground, Field(discriminator="type")
]


class Animation(ContractModel):
    """An explicit editor animation override; null means planner-selected motion."""

    type: Literal["none", "fade_in", "slide_up", "slide_left", "zoom_in", "pop"]
    delay_ms: int = Field(default=0, ge=0, le=5000)
    duration_ms: int = Field(default=400, ge=100, le=2000)


class TextElement(ContractModel):
    """Resolved text primitive rendered by a layout preset."""

    id: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=200)
    role: Literal["heading", "body", "caption", "stat"]
    position: Literal["top", "center", "bottom"]
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    highlight_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    animation: Animation | None = None


class ImageElement(ContractModel):
    """Resolved image primitive."""

    id: str = Field(min_length=1)
    asset: AssetRef
    fit: Literal["cover", "contain"] = "cover"
    ken_burns: bool = True
    caption: str | None = Field(default=None, max_length=80)
    animation: Animation | None = None


class WordTimestamp(ContractModel):
    """A word-level audio timestamp produced by the voice worker."""

    word: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class AudioSpec(ContractModel):
    """Produced voice asset metadata."""

    path: str = Field(min_length=1)
    duration_ms: int = Field(gt=0)
    timestamps: list[WordTimestamp] = Field(default_factory=list)


class VoiceSpec(ContractModel):
    """Narration intent and optional produced audio."""

    text: str = Field(min_length=1, max_length=500)
    voice_id: str = Field(min_length=1)
    speed: float = Field(default=1.0, ge=0.8, le=1.3)
    audio: AudioSpec | None = None


class SubtitleSpec(ContractModel):
    """Subtitle render preference."""

    enabled: bool = True
    style: Literal["line", "karaoke"] = "line"


class Transition(ContractModel):
    """Transition out of a scene, assembled after individual scene renders."""

    type: Literal["none", "fade", "slide_left", "slide_up", "zoom"]
    duration_ms: int = Field(ge=200, le=1500)


class BgmSpec(ContractModel):
    """Project-wide background music."""

    asset_id: str = Field(min_length=1)
    volume: float = Field(ge=0, le=1)
    fade_out_ms: int = Field(ge=0)


class MotionSyncPoint(ContractModel):
    """A timestamped deterministic motion cue."""

    at_ms: int = Field(ge=0)
    effect: str = Field(min_length=1)
    target: str = Field(min_length=1)


class MotionTrack(ContractModel):
    """A planned motion track for one resolved component."""

    component_id: str = Field(min_length=1)
    preset: str = Field(min_length=1)
    reason: Literal["narration_sync", "hierarchy", "sequence"]
    enter_at_ms: int = Field(ge=0)
    end_by_ms: int | None = Field(default=None, ge=0)
    sync_points: list[MotionSyncPoint] = Field(default_factory=list)


class MotionPlan(ContractModel):
    """Deterministic output of the motion planner (pass-1 estimated timing)."""

    tracks: list[MotionTrack] = Field(default_factory=list)
    transition_out_type: str = Field(default="fade", min_length=1)
    transition_out_duration_ms: int = Field(default=500, ge=200, le=1500)


class Scene(ContractModel):
    """Resolved scene input for a Remotion composition."""

    scene_id: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    scene_number: int = Field(ge=1)
    duration_ms: int = Field(ge=1000, le=30000)
    layout: LayoutName
    background: Background
    texts: list[TextElement] = Field(default_factory=list, max_length=8)
    images: list[ImageElement] = Field(default_factory=list, max_length=3)
    voice: VoiceSpec | None = None
    subtitle: SubtitleSpec = Field(default_factory=SubtitleSpec)
    transition: Transition
    motion_plan: MotionPlan | None = None
    semantic_tree: dict[str, object] | None = None
    layout_override: LayoutName | None = None

    @model_validator(mode="after")
    def ensure_unique_element_ids(self) -> Scene:
        """Keep primitive identifiers unambiguous for motion tracks and editor diffs."""

        identifiers = [element.id for element in self.texts]
        identifiers.extend(element.id for element in self.images)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("texts and images must not reuse an id")
        return self


class VideoProject(ContractModel):
    """The root resolved render contract."""

    project_id: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    format: Format
    platform_profile: PlatformProfile = "generic"
    fps: int = Field(default=30, ge=1, le=120)
    scenes: list[Scene] = Field(min_length=1)
    bgm: BgmSpec | None = None
    watermark: ImageElement | None = None

    @model_validator(mode="after")
    def validate_platform_format(self) -> VideoProject:
        """Prevent a platform profile from selecting an incompatible output shape."""

        vertical_profiles = {"tiktok", "facebook_reels", "youtube_shorts"}
        if self.platform_profile in vertical_profiles and self.format != "vertical_1080x1920":
            raise ValueError("platform_profile requires vertical_1080x1920")
        if self.platform_profile == "youtube_video" and self.format != "horizontal_1920x1080":
            raise ValueError("youtube_video requires horizontal_1920x1080")
        return self


def _canonical_value(value: object, *, is_project_root: bool = False) -> object:
    """Normalize a contract value into the stable cache-key representation."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True, exclude_none=False)
    if isinstance(value, str):
        return normalize("NFC", value)
    if isinstance(value, list):
        normalized = [_canonical_value(item) for item in value]
        if is_project_root:
            return sorted(
                normalized,
                key=lambda item: json.dumps(
                    item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            )
        return normalized
    if isinstance(value, dict):
        return {
            normalize("NFC", str(key)): _canonical_value(
                item, is_project_root=key == "scenes"
            )
            for key, item in value.items()
            if key != "scene_number"
        }
    return value


def canonical_hash(scene_or_project: Scene | VideoProject | dict[str, object]) -> str:
    """Hash canonical JSON, ignoring scene ordinal and project scene ordering."""

    canonical = _canonical_value(scene_or_project)
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SemanticComponent(ContractModel):
    """Content intent emitted by AI, intentionally without visual layout fields."""

    kind: Literal[
        "heading",
        "body",
        "media_intent",
        "stat",
        "bullet",
        "chart_data",
        "table_data",
        "quote",
        "code",
        "group",
    ]
    text: str | None = None
    value: str | None = None
    suffix: str | None = None
    label: str | None = None
    source_id: str | None = None
    query_vi: str | None = None
    media_hint: Literal["diagram", "photo", "screenshot", "logo"] | None = None
    emphasis: list[str] = Field(default_factory=list)
    author: str | None = None
    unit: str | None = None
    points: list[dict[str, object]] = Field(default_factory=list)
    col_a: str | None = None
    col_b: str | None = None
    rows: list[dict[str, object]] = Field(default_factory=list)
    content: str | None = None
    language: str | None = None
    children: list[SemanticComponent] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_sources_for_verifiable_content(self) -> SemanticComponent:
        """Keep fact-check provenance attached to claims and quotations."""

        if self.kind in {"stat", "chart_data", "table_data", "quote"} and not self.source_id:
            raise ValueError(f"{self.kind} requires source_id")
        return self


class SemanticScene(ContractModel):
    """One AI-authored semantic scene with no rendering instructions."""

    purpose: Literal[
        "hook",
        "explain",
        "evidence",
        "compare",
        "steps",
        "quote",
        "demo",
        "conclusion",
        "cta",
    ]
    narration: str = Field(min_length=1, max_length=500)
    components: list[SemanticComponent] = Field(min_length=1, max_length=8)


class SemanticStoryboard(ContractModel):
    """Strict boundary model for untrusted LLM storyboard output."""

    scenes: list[SemanticScene] = Field(min_length=1)
