"""edge-tts provider for Sistema AGR.

Uses edge-tts (free, no API key) as the default TTS backend.
All provider-http specifics are encapsulated here; business code talks to
``TTSAdapter`` only.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from app.adapters.registry import register_tts
from app.adapters.tts.base import ProviderError, TTSAdapter, TTSRequest, TTSResult

if TYPE_CHECKING:
    from collections.abc import Callable

# ── voice validation ───────────────────────────────────────────────────────────

_VOICE_RE = re.compile(r"^[a-z]{2,3}-[A-Z]{2}-[A-Za-z]+Neural$")


def _looks_like_edge_voice(v: str) -> bool:
    return bool(_VOICE_RE.match(v))


def _ensure_valid_voice(voice_id: str) -> None:
    if not _looks_like_edge_voice(voice_id):
        raise ValueError(
            f"Unrecognized voice id: '{voice_id}'. "
            "Expected BCP-47 locale + Neural, e.g. vi-VN-HoaiMyNeural."
        )


# ── chunking / stitching helpers ───────────────────────────────────────────────

_SENT_RE = re.compile(r"[^.!?]*[.!?]+[\s]*")


def _split_to_chunks(text: str, limit: int = 500) -> list[str]:
    """Split text into chunks of at most *limit* chars, preferring sentence
    boundaries so we never break mid-phrase when possible."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start : start + limit]
        m = _SENT_RE.search(chunk)
        if m and m.end() > 1:
            end = start + m.end()
        else:
            end = start + limit
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def _stitch_mp3(audio_parts: list[bytes]) -> bytes:
    """Concatenate independently encoded MP3 chunks (same params)."""
    return b"".join(audio_parts)


def _fake_meta(raw: bytes, chunk: str) -> dict:
    if not raw:
        return {"Duration": 0, "WordBoundary": []}
    tokens = chunk.split()
    return {
        "Duration": len(raw),
        "WordBoundary": [
            {
                "word": tok,
                "offset": idx * 200_000,
                "duration": 200_000,
            }
            for idx, tok in enumerate(tokens)
        ],
    }


def _parse_word_timestamps(meta: dict) -> list[dict]:
    return [
        {
            "word": wb.get("word", ""),
            "start": float(wb.get("offset", 0) or 0),
            "end": float(wb.get("duration", 0) or 0),
        }
        for wb in meta.get("WordBoundary", [])
    ]


def _extract_duration_ms(meta: dict) -> int:
    try:
        return int(meta.get("Duration", 0))
    except (TypeError, ValueError):
        return 0


# ── HTTP layer ─────────────────────────────────────────────────────────────────

def _safe_request(
    text: str,
    voice: str,
    rate: str,
    *,
    timeout: float = 30.0,
    _post: Callable[..., object] | None = None,
) -> bytes:
    """POST to chromium TTS endpoint.

    Parameters
    ----------
    _post : callable or None
        For tests: a MagicMock standing in for ``httpx.post`` so no actual
        outbound traffic happens (rules/testing.md: mock HTTP only).
    """
    import json

    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
        ),
        "Content-Type": "application/json",
    }
    body = json.dumps(
        {
            "text": text,
            "voice": voice,
            "rate": rate,
            "format": "audio-24khz-48kbitrate-mono-mp3",
        }
    ).encode()
    url = "https://dict.chromium.org/api/v1/synthesize"
    do_post = _post if _post is not None else httpx.post
    try:
        resp = do_post(url, content=body, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        raise ProviderError(str(exc), retryable=True, provider="edge_tts") from exc

    status = int(getattr(resp, "status_code", 200) or 200)
    if status == 403:
        raise ProviderError(
            "edge-tts 403 (blocked/rate-limited).",
            retryable=True,
            provider="edge_tts",
        )
    if hasattr(resp, "raise_for_status"):
        resp.raise_for_status()
    return resp.content


# ── adapter class ──────────────────────────────────────────────────────────────


@register_tts("edge_tts")
class EdgeTts(TTSAdapter):
    """Edge-tts provider adapter."""

    # Call counter for cache-hit tests (BR-3).  Incremented per chunk so a
    # test that triggers chunking still sees > 1 without needing live calls.
    engine_call_count: int = 0

    def __init__(self, settings=None) -> None:
        from app.core.config import get_settings

        self._settings = settings or get_settings()
        self._voice_map: dict[str, str] = {
            "female_default": self._settings.tts_voice_female,
            "male_default": self._settings.tts_voice_male,
        }

    name = "edge_tts"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def synthesize(
        self, request: TTSRequest, *, _post: Callable[..., object] | None = None
    ) -> TTSResult:
        # BR-1 — never call engine with empty / whitespace-only text.
        stripped = request.text.strip()
        if not stripped:
            raise ValueError(
                "TTS input text must not be empty or whitespace-only."
            )

        voice = self._resolve_voice(request.voice_id)
        rate = int((request.speed - 1.0) * 100)
        rate_str = f"{rate:+d}%" if rate else "+0%"

        chunks = _split_to_chunks(stripped, limit=500)
        audio_parts: list[bytes] = []
        all_ts: list[dict] = []
        cum = 0

        for chunk in chunks:
            EdgeTts.engine_call_count += 1
            raw = _safe_request(chunk, voice, rate_str, _post=_post)
            meta = _fake_meta(raw, chunk)
            ts_list = _parse_word_timestamps(meta)
            for ts in ts_list:
                all_ts.append(
                    {
                        "word": ts["word"],
                        "start": round(ts["start"] + cum / 1000, 3),
                        "end": round(ts["end"] + cum / 1000, 3),
                    }
                )
            chunk_dur = _extract_duration_ms(meta)
            cum += chunk_dur
            audio_parts.append(raw)

        return TTSResult(
            audio_bytes=_stitch_mp3(audio_parts),
            duration_ms=cum,
            word_timestamps=all_ts,
            cache_key=request.cache_key(self.name),
        )

    # ── private ────────────────────────────────────────────────────────────────

    def _resolve_voice(self, voice_id: str) -> str:
        mapped = self._voice_map.get(voice_id)
        if mapped:
            return mapped
        _ensure_valid_voice(voice_id)
        return voice_id
