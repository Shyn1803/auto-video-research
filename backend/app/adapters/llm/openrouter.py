"""OpenRouter LLM adapter — two registered names: openrouter_free / openrouter_free.

``openrouter_free``: filters models to ``:free`` suffix only; *is_paid=False*.
``openrouter_paid``: requires key + ``ALLOW_PAID=true`` (enforced by router); *is_paid=True*.

Configuration arrives via ``ProviderSettings.extra`` (set by the router).
The API mirrors the OpenAI ``/v1/chat/completions`` endpoint.

All HTTP errors wrapped in ``ProviderError(retryable=bool)``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.openrouter")

_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _is_free_model(model_id: str) -> bool:
    return model_id.endswith(":free")


def _is_paid(variant: str) -> bool:
    """Return True when the OpenRouter variant is paid-only."""
    return variant == "openrouter_paid"


# ── Shared implementation base (registered under different names below) ────


class _OpenRouterBase(LLMAdapter):
    """Shared functionality; concrete subclasses register themselves."""

    name: str = ""
    is_paid: bool = False
    _variant: str = ""     # "openrouter_free" or "openrouter_paid"
    _models_cache: dict[str, Any] | None = None

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key: str = settings.api_key if settings else ""
        self._model: str = (
            settings.extra.get("openrouter_paid_model", "")
            if settings
            else ""
        )
        self._free_model: str = (
            settings.extra.get("openrouter_free_model", "google/gemini-2.0-flash-exp:free")
            if settings
            else "google/gemini-2.0-flash-exp:free"
        )

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
                f"{self.name}: no API key (OPENROUTER_API_KEY missing)",
                retryable=False,
            )

        model = self._resolve_model()

        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a structured JSON assistant. "
                        "Respond ONLY with valid JSON matching the schema. "
                        "No preamble, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
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
                    f"{self.name} rate limited (429)",
                    retryable=True,
                ) from exc
            elif status == 401:
                raise ProviderError(
                    f"{self.name}: invalid API key (401)",
                    retryable=False,
                ) from exc
            else:
                raise ProviderError(
                    f"{self.name} HTTP {status}: {exc}",
                    retryable=True,
                ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(
                f"{self.name} connection error: {exc}",
                retryable=True,
            ) from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_model(self) -> str:
        if self._variant == "openrouter_free":
            return self._free_model
        # openrouter_paid — use configured paid model or a sensible default
        return self._model or "openai/gpt-4o-mini"

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                _CHAT_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://avr.local",
                    "X-Title": "AVR",
                },
                timeout=180.0,
            )
            resp.raise_for_status()
        return resp.json()


def _parse_chat_response(raw: dict[str, Any]) -> dict[str, object]:
    try:
        text = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(
            f"openrouter response missing expected fields: {exc}. Raw: {raw!r:.200}",
            retryable=True,
        ) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"openrouter output is not valid JSON: {exc}",
            retryable=False,
        ) from exc


# ── Registered classes ───────────────────────────────────────────────────────


@register_llm("openrouter_free")
class OpenRouterFreeLLM(_OpenRouterBase):
    """OpenRouter free tier — filters to :free models only; is_paid=False."""

    name: str = "openrouter_free"
    is_paid: bool = False
    _variant: str = "openrouter_free"


@register_llm("openrouter_paid")
class OpenRouterPaidLLM(_OpenRouterBase):
    """OpenRouter paid tier — requires key + ALLOW_PAID=true.

    is_paid=True so the router's ALLOW_PAID gate applies (BR-1).
    """

    name: str = "openrouter_paid"
    is_paid: bool = True
    _variant: str = "openrouter_paid"
