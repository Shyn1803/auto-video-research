"""Groq LLM adapter — free tier, OpenAI-compatible API.

Configuration arrives via ``ProviderSettings.extra`` (set by the router).
Groq exposes an OpenAI-compatible ``/v1/chat/completions`` endpoint.

All HTTP errors wrapped in ``ProviderError(retryable=bool)``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.groq")

_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


@register_llm("groq")
class GroqLLM(LLMAdapter):
    """Groq adapter — free tier, OpenAI-compatible."""

    name: str = "groq"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key: str = self.settings.api_key
        self._model: str = self.settings.extra.get("groq_model", "llama-3.3-70b-versatile")

    # ------------------------------------------------------------------
    # available()
    # ------------------------------------------------------------------

    async def available(self) -> bool:
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
        if not self._api_key:
            raise ProviderError(
                "groq: no API key (GROQ_API_KEY missing)",
                retryable=False,
            )

        system_prompt = (
            "You are a structured JSON assistant. "
            "Respond ONLY with valid JSON matching this schema — "
            "no preamble, no markdown fences, no explanation outside the JSON."
        )
        response_schema_str = json.dumps(schema, ensure_ascii=False)

        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            raw = await self._post(body)
            return _parse_chat_response(raw)
        except ProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ProviderError(
                    f"groq rate limited (429): {exc}",
                    retryable=True,
                ) from exc
            elif status == 401:
                raise ProviderError(
                    "groq: invalid API key (401)",
                    retryable=False,
                ) from exc
            else:
                raise ProviderError(
                    f"groq HTTP {status}: {exc}",
                    retryable=True,
                ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(
                f"groq connection error: {exc}",
                retryable=True,
            ) from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                _CHAT_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
            resp.raise_for_status()
        return resp.json()


# ── Helpers (testable in isolation) ──────────────────────────────────────────


def _parse_chat_response(raw: dict[str, Any]) -> dict[str, object]:
    try:
        text = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            f"groq response missing expected fields: {exc}. Raw: {raw!r:.200}",
            retryable=True,
        ) from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"groq output is not valid JSON: {exc}",
            retryable=False,
        ) from exc
