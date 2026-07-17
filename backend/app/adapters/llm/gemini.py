"""Gemini LLM adapter — free tier via ``GEMINI_API_KEY``.

Configuration arrives via ``ProviderSettings.extra`` (set by the router).
Structured output uses the ``responseSchema`` parameter.

All HTTP errors wrapped in ``ProviderError(retryable=bool)``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.gemini")

_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


@register_llm("gemini")
class GeminiLLM(LLMAdapter):
    """Google Gemini adapter — free tier available with API key."""

    name: str = "gemini"
    is_paid: bool = False  # Free tier available; paid usage still free-tier-gated

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key: str = self.settings.api_key
        self._model: str = self.settings.extra.get(
            "gemini_model", "gemini-flash-latest"
        )

    # ------------------------------------------------------------------
    # available()
    # ------------------------------------------------------------------

    async def available(self) -> bool:
        """Available when an API key is present (no outbound call needed)."""
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # call_structured()
    # ------------------------------------------------------------------

    async def call_structured(
        self,
        prompt: str,
        schema: dict[str, object],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        tier: str = "cheap",
    ) -> dict[str, object]:
        """Call Gemini with ``responseSchema`` for structured JSON output."""
        if not self._api_key:
            raise ProviderError(
                "gemini: no API key configured (GEMINI_API_KEY missing)",
                retryable=False,
            )

        url = _GENERATE_URL.format(model=self._model)
        params = {"key": self._api_key}

        body = _build_gemini_body(prompt, schema, temperature, max_tokens)

        try:
            raw = await self._post(url, params, body)
            return _parse_gemini_response(raw)
        except ProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ProviderError(
                    f"gemini rate limited (429): {exc}",
                    retryable=True,
                ) from exc
            elif status == 403:
                raise ProviderError(
                    f"gemini forbidden (403) — invalid/expired key",
                    retryable=False,
                ) from exc
            elif status == 400:
                detail = exc.response.text[:200]
                raise ProviderError(
                    f"gemini bad request (400): {detail}",
                    retryable=False,
                ) from exc
            else:
                raise ProviderError(
                    f"gemini HTTP {status}: {exc}",
                    retryable=True,
                ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(
                f"gemini connection error: {exc}",
                retryable=True,
            ) from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _post(
        self, url: str, params: dict[str, str], body: dict[str, Any]
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url, params=params, json=body, timeout=120.0
            )
            resp.raise_for_status()
        return resp.json()


# ── Helper functions (module-level — testable in isolation) ──────────────────


def _build_gemini_body(
    prompt: str,
    schema: dict[str, object],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Build the Gemini ``contents`` + ``generationConfig`` request body."""
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            "responseSchema": _sanitize_schema(_normalize_schema(schema)),
        },
    }


def _normalize_schema(schema: dict[str, object]) -> dict[str, object]:
    """Wrap a bare field-map (no top-level ``type``) into an object schema.

    Callers may pass either a full JSON Schema (``{"type": "object",
    "properties": {...}}``) or a shorthand field-map (``{"field": {"type":
    "string"}}``). Gemini's ``responseSchema`` always requires the former.
    """
    if "type" not in schema:
        return {"type": "object", "properties": schema}
    return schema


def _sanitize_schema(schema: dict[str, object]) -> dict[str, object]:
    """Strip non-JSON-Schema keys that Gemini doesn't accept (recursively)."""
    ACCEPTED_KEYS = {
        "type",
        "properties",
        "required",
        "items",
        "enum",
        "format",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    }
    out: dict[str, object] = {}
    for k, v in schema.items():
        if k == "properties" and isinstance(v, dict):
            out[k] = {
                pk: (_sanitize_schema(pv) if isinstance(pv, dict) else pv)
                for pk, pv in v.items()
            }
        elif k == "items" and isinstance(v, dict):
            out[k] = _sanitize_schema(v)
        elif k in ACCEPTED_KEYS:
            out[k] = v
        elif k == "anyOf" and isinstance(v, list):
            out[k] = [
                _sanitize_schema(alt) if isinstance(alt, dict) else alt
                for alt in v
            ]
    return out


def _parse_gemini_response(raw: dict[str, Any]) -> dict[str, object]:
    """Extract structured JSON from Gemini's response."""
    try:
        candidates = raw["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            f"gemini response missing expected fields: {exc}. Raw: {raw!r:.200}",
            retryable=True,
        ) from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"gemini output is not valid JSON: {exc}",
            retryable=False,
        ) from exc
