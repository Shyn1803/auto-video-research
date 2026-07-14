"""Abstract base classes for all provider adapters.

One ABC per capability (7 total in v1).  Each declares ``name``,
``is_paid``, an ``available()`` readiness check, and the single
capability-specific method.  Adapters receive config via
``ProviderSettings`` — never read ``os.environ`` directly.  All
external exceptions must be wrapped in ``ProviderError``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderSettings:
    """Typed config for a single adapter invocation.

    Filled by ``app.core.config`` from env / DB / defaults — adapters
    must NOT call ``os.environ`` or ``os.getenv`` directly.
    """

    provider_name: str = ""
    api_key: str = ""
    base_url: str = ""
    extra: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Unified error raised by every adapter on failure.

    Attributes:
        retryable: ``True`` when the caller / retry loop should attempt
        again (timeout, 5xx, rate-limit).  ``False`` for terminal errors
        (auth failure, invalid request, quota exhausted permanently).
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


# ---------------------------------------------------------------------------
# TTS value types (shared between base and edge_tts)
# ---------------------------------------------------------------------------

class TTSResult:
    """Output of a successful TTS synthesis call."""

    __slots__ = ("audio_bytes", "duration_ms", "word_timestamps", "cache_key")

    def __init__(
        self,
        audio_bytes: bytes,
        duration_ms: int,
        word_timestamps: list[dict[str, object]],
        cache_key: str = "",
    ) -> None:
        self.audio_bytes = audio_bytes
        self.duration_ms = duration_ms
        self.word_timestamps = word_timestamps
        self.cache_key = cache_key

    @staticmethod
    def cache_key(text: str, voice_id: str, speed: float, engine: str) -> str:
        """Content-addressed key for deduplication cache lookups."""
        import hashlib
        raw = f"{text}\x00{voice_id}\x00{speed}\x00{engine}"
        return hashlib.sha256(raw.encode()).hexdigest()


class TTSRequest:
    """Immutable input for a single TTS synthesis call."""

    __slots__ = ("text", "voice_id", "speed")

    def __init__(self, text: str, voice_id: str, speed: float = 1.0) -> None:
        self.text = text
        self.voice_id = voice_id
        self.speed = speed


# ---------------------------------------------------------------------------
# Capability ABCs
# ---------------------------------------------------------------------------

class BaseAdapter(ABC):
    """Common contract shared by every capability adapter.

    Subclasses must declare ``name`` and ``is_paid`` as class attributes
    (not property methods) so the registry can read them without
    instantiation.  ``is_paid`` defaults to ``True`` — a forgotten
    override is cost-safe, never cost-unsafe (BR-4).
    """

    name: str = ""
    is_paid: bool = True

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        self.settings: ProviderSettings = settings or ProviderSettings()

    @abstractmethod
    async def available(self) -> bool:
        """Return ``True`` when this provider can accept work.

        Typically checks config (key present, base_url reachable).
        Called before every invocation; no side effects.
        """


class LLMAdapter(BaseAdapter):
    """Large-language-model adapter."""

    @abstractmethod
    async def call_structured(
        self,
        prompt: str,
        schema: dict[str, object],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict[str, object]:
        """Return structured JSON matching *schema* for *prompt*.

        Raises:
            ProviderError: on any failure (network, auth, rate-limit ...).
                Set ``retryable=True`` when the caller should rotate
                key / provider and retry, ``False`` for hard failures.
        """


class TTSAdapter(BaseAdapter):
    """Text-to-speech adapter."""

    @abstractmethod
    async def synthesize(
        self,
        request: TTSRequest,
    ) -> TTSResult:
        """Return synthesized audio plus metadata.

        Raises:
            ProviderError: on any failure.
        """


class SearchAdapter(BaseAdapter):
    """Web-search / crawl adapter."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "vi",
    ) -> list[dict[str, str]]:
        """Return a list of result dicts (at minimum ``title``, ``url``,
        ``snippet``).

        Raises:
            ProviderError: on any failure.
        """


class ImageGenAdapter(BaseAdapter):
    """Image generation adapter (Stable Diffusion, DALL-E, etc.)."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
    ) -> bytes:
        """Return raw image bytes (PNG / JPEG).

        Raises:
            ProviderError: on any failure.
        """


class AssetStockAdapter(BaseAdapter):
    """Stock-photo / asset search adapter (Pexels, Unsplash ...)."""

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        license_: str = "free",
    ) -> list[dict[str, str]]:
        """Return a list of asset dicts (at minimum ``url``, ``thumb_url``,
        ``attribution``, ``license``).

        Raises:
            ProviderError: on any failure.
        """


class StorageAdapter(BaseAdapter):
    """Object-storage adapter (MinIO / S3-compatible)."""

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload *data* under *key*; return the public URL.

        Raises:
            ProviderError: on any failure.
        """

    @abstractmethod
    async def presign_get(
        self,
        key: str,
        *,
        expires_seconds: int = 3600,
    ) -> str:
        """Return a pre-signed GET URL for *key*.

        Raises:
            ProviderError: on any failure.
        """


class PublishAdapter(BaseAdapter):
    """Platform-publish adapter (YouTube, TikTok, download ...)."""

    @abstractmethod
    async def publish(
        self,
        video_url: str,
        *,
        title: str = "",
        description: str = "",
        tags: list[str] | None = None,
        callback_url: str = "",
    ) -> dict[str, str]:
        """Publish the video at *video_url*; return at minimum
        ``platform_post_id`` and ``url``.

        Raises:
            ProviderError: on any failure.
        """
