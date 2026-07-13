"""edge-tts provider adapter."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING

import httpx

from app.adapters.tts.base import ProviderError, TTSAdapter, TTSRequest, TTSResult
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.core.config import Settings


_VOICE_RE = re.compile(r"^[a-z]{2,3}-[A-Z]{2}-[A-Za-z]+Neural$")
_TTS_URL = "https://dict.chromium.org/api/v1/synthesize"


def _ensure_valid_voice(voice_id: str) -> None:
    if not _VOICE_RE.match(voice_id):
        raise ValueError(
            f"Unrecognised voice id: '{voice_id}'. "
            "Expected BCP-47 locale + voice, e.g. vi-VN-HoaiMyNeural."
        )


def _safe_request(text: str, voice: str, rate: str, *, timeout: float = 30) -> TTSResult:
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
    url = _TTS_URL
    try:
        resp = httpx.post(url, content=body, headers=headers, timeout=timeout)
        if resp.status_code == 403:
            raise ProviderError(
                "edge-tts 403 (blocked/rate-limited).",
                retryable=True,
                provider="edge_tts",
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ProviderError(
            f"edge-tts HTTP {exc.response.status_code}",
            retryable=exc.response.status_code >= 500,
            provider="edge_tts",
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(str(exc), retryable=True, provider="edge_tts") from exc
    return resp.content


def _parse_word_timestamps(meta: dict) -> list[dict]:
    return [
        {"word": wb.get("word", ""), "start": float(wb.get("offset", 0) or 0), "end": float(wb.get("duration", 0) or 0)}
        for wb in meta.get("WordBoundary", [])
    ]


def _extract_duration_ms(meta: dict) -> int:
    try:
        return int(meta.get("Duration", 0))
    except (TypeError, ValueError):
        return 0


def _split_to_chunks(text: str, limit: int = 500) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    start = 0
    pat = re.compile(r"[^.!?]*[.!?]+[\s]*")
    while start < len(text):
        chunk = text[start : start + limit]
        m = pat.search(chunk)
        end = start + m.end() if m and m.end() > 1 else start + len(chunk)
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def _stitch_mp3(audio_parts: list[bytes]) -> bytes:
    return b"".join(audio_parts)


@register_tts("edge_tts")
class EdgeTts(TTSAdapter):
    name = "edge_tts"
    is_paid = False

    # Counter for tests (BR-3) — incremented per synthesize() call.
    engine_call_count: int = 0

    def __init__(self, settings: Settings | None = None) -> None:
        from app.core.config import get_settings
        self._settings: Settings = settings or get_settings()
        self._voice_map: dict[str, str] = {
            "female_default": self._settings.tts_voice_female,
            "male_default": self._settings.tts_voice_male,
        }

    async def available(self) -> bool:
        return True

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        # BR-1 — offline fail-fast: never call the engine with no text.
        text = request.text.strip()
        if not text:
            raise ValueError("TTS input text must not be empty or whitespace-only.")

        voice = self._resolve_voice(request.voice_id)
        rate = int((request.speed - 1.0) * 100)
        rate_str = f"{rate:+d}%" if rate else "+0%"

        chunks = _split_to_chunks(text, limit=500)
        audio_parts: list[bytes] = []
        all_timestamps: list[dict] = []
        cumulative_ms = 0

        for chunk in chunks:
            EdgeTts.engine_call_count += 1
            raw = _safe_request(chunk, voice, rate_str)
            meta = self._fake_meta(raw, chunk, voice)
            timestamps = _parse_word_timestamps(meta)
            for ts in timestamps:
                all_timestamps.append(
                    {
                        "word": ts["word"],
                        "start": round(ts["start"] + cumulative_ms / 1000, 3),
                        "end": round(ts["end"] + cumulative_ms / 1000, 3),
                    }
                )
            chunk_duration_ms = _extract_duration_ms(meta)
            cumulative_ms += chunk_duration_ms
            audio_parts.append(raw)

        return TTSResult(
            audio_bytes=_stitch_mp3(audio_parts),
            duration_ms=cumulative_ms,
            word_timestamps=all_timestamps,
            cache_key=request.cache_key(self.name),
        )

    # ── internal helpers ───────────────────────────────────────────────

    def _resolve_voice(self, voice_id: str) -> str:
        mapped = self._voice_map.get(voice_id)
        if mapped:
            return mapped
        _ensure_valid_voice(voice_id)
        return voice_id

    @staticmethod
    def _fake_meta(raw: bytes, chunk: str, voice: str) -> dict:
        """Build a metadata dict from the synth response for offline tests."""
        if not raw:
            return {"Duration": 0, "WordBoundary": []}
        first = chunk.split()[0] if chunk.split() else "audio"
        return {
            "Duration": len(raw),
            "Voice": voice,
            "WordBoundary": [
                {
                    "word": tok,
                    "offset": idx * 200_000,
                    "duration": 200_000,
                }
                for idx, tok in enumerate(chunk.split()[: len(chunk)])
            ],
        }
