"""Ollama LLM adapter — local, free, always-available baseline.

Configuration arrives via ProviderSettings.extra (set by the router,
never read from os.environ). Uses Ollama's native JSON mode for
structured output.

Key/health contracts:
- available(): fast health-check against ollama_url /api/tags.
- call_structured: POST /api/generate with format=schema, return parsed dict.

All HTTP errors wrapped in ProviderError(retryable=bool).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.ollama")

_TAGS_PATH = "/api/tags"
_GENERATE_PATH = "/api/generate"


@register_llm("ollama")
class OllamaLLM(LLMAdapter):
    """Local Ollama LLM — free, no API key required."""

    name: str = "ollama"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._base_url: str = self.settings.extra.get(
            "ollama_url", "http://localhost:11434"
        ).rstrip("/")
        self._model_cheap: str = self.settings.extra.get(
            "ollama_model_cheap", "qwen2.5:14b-instruct"
        )
        self._model_strong: str = self.settings.extra.get(
            "ollama_model_strong", "qwen2.5:32b-instruct"
        )

    async def available(self) -> bool:
        """Return True when the Ollama service is reachable and responsive."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}{_TAGS_PATH}"
                )
                resp.raise_for_status()
            return True
        except (httpx.HTTPError, OSError) as exc:
            logger.debug("ollama unavailable: %s", exc)
            return False

    async def call_structured(
        self,
        prompt: str,
        schema: dict[str, object],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        tier: str = "cheap",
    ) -> dict[str, object]:
        """Call Ollama in JSON mode and return a dict matching *schema*."""
        model = (
            self._model_strong
            if tier == "strong"
            else self._model_cheap
        )
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            raw = await self._post_generate(payload)
            return self._parse_response(raw, prompt)
        except ProviderError:
            raise
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(
                f"ollama HTTP error: {exc}",
                retryable=True,
            ) from exc
        except Exception as exc:
            raise ProviderError(
                f"ollama unexpected error: {exc}",
                retryable=False,
            ) from exc

    async def _post_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self._base_url}{_GENERATE_PATH}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=180.0,
            )
            if resp.status_code == 404:
                raise ProviderError(
                    f"ollama model not found (404 from {self._base_url})",
                    retryable=False,
                )
            if resp.status_code == 400:
                body = resp.text[:300]
                raise ProviderError(
                    f"ollama bad request (400): {body}",
                    retryable=False,
                )
            resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_response(
        raw: dict[str, Any], prompt_snippet: str
    ) -> dict[str, object]:
        text = raw.get("response")
        if text is None:
            raise ProviderError(
                "ollama returned no 'response' field",
                retryable=True,
            )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.debug(
                "ollama JSON parse error prompt=%r text=%s err=%s",
                prompt_snippet[:80],
                text[:200],
                exc,
            )
            raise ProviderError(
                f"ollama response is not valid JSON: {exc}",
                retryable=False,
            ) from exc
