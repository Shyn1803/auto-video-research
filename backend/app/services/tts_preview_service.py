"""TTS preview service — used by the Create-project modal for voice audition (BR-5).

All calls go through the TTS adapter boundary (never call edge-tts directly
from this module). Results are content-addressed and cached for the lifetime
of the process.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import ClassVar

from app.adapters.registry import get_registered
from app.adapters.tts.base import TTSAdapter, TTSRequest, TTSResult

logger = logging.getLogger(__name__)

# Fixed sample sentence for voice previews — cache key is stable.
SAMPLE_TEXT = (
    "Xin chào, đây là giọng đọc mẫu cho dự án của bạn."
)

# Voice map — overridden from config when ProviderSettings include a voice_map.
SAMPLE_VOICE_MAP: dict[str, str] = {
    "female": "vi-VN-HoaiMyNeural",
    "male": "vi-VN-NamMinhNeural",
}

_cache: dict[str, tuple[bytes, int]] = {}


def _cache_key(engine: str, voice: str, text: str) -> str:
    raw = f"{engine}\x00{voice}\x00{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# Read the configuration from env/db before any provider is instantiated.
from app.core.config import get_settings as _get_settings  # noqa: E402  (cycle-safe at module level for Settings.Read)


def _resolve_voice(voice_gender: str) -> str:
    settings = _get_settings()
    map_ = {
        "female": (settings.tts_voice_female or SAMPLE_VOICE_MAP["female"]),
        "male": (settings.tts_voice_male or SAMPLE_VOICE_MAP["male"]),
    }
    return map_.get(voice_gender, map_["female"])


@asynccontextmanager
async def _adapter() -> AsyncIterator[TTSAdapter | None]:
    """Resolve the first available TTS adapter from the registry."""
    classes = get_registered("tts")
    for _name, cls in classes.items():
        adapter = cls()
        if await adapter.available():
            yield adapter
            return
    yield None  # nothing available


async def tts_preview(voice_gender: str = "female") -> tuple[bytes, int]:
    """Synthesise the fixed sample sentence.

    Returns ``(audio_bytes, duration_ms)``.

    Raises:
        ProviderError – when no TTS adapter is registered/available.
    """
    from app.adapters.tts.base import ProviderError  # inside fn to let callers catch it

    voice = _resolve_voice(voice_gender)
    cache_key = _cache_key("edge_tts", voice, SAMPLE_TEXT)
    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug("TTS preview cache hit (key=%s)", cache_key[:12])
        return cached

    async with _adapter() as adapter:
        if adapter is None:
            raise ProviderError(
                "no TTS adapter registered/available", retryable=False
            )

        req = TTSRequest(text=SAMPLE_TEXT, voice_id=voice, speed=1.0)
        result: TTSResult = await adapter.synthesize(req)

    logger.info(
        "tts_preview synthesised provider=%s duration_ms=%d",
        getattr(adapter, "name", "?"),
        result.duration_ms,
    )
    _cache[cache_key] = (result.audio_bytes, result.duration_ms)
    return result.audio_bytes, result.duration_ms
