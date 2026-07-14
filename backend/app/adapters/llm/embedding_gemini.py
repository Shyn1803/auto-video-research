"""Gemini embedding adapter — uses ``GEMINI_API_KEY``.

The Gemini embedding endpoint is ``POST /v1beta/models/{model}:embedContent``.
For semantic search / similarity, the ``gemini_embedding`` provider is listed
in the ``EMBEDDING_CHAIN`` after ``bge_m3_local`` (so the local model is
tried first, falling back to cloud).

All HTTP errors wrapped in ``ProviderError``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.gemini_embed")

_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
)
_DEFAULT_MODEL = "text-embedding-004"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity — pure math, no external dependency."""
    if len(a) != len(b):
        raise ValueError("vectors must be the same length")
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


@register_llm("gemini_embedding")
class GeminiEmbeddingLLM(LLMAdapter):
    """Gemini text-embedding adapter."""

    name: str = "gemini_embedding"
    is_paid: bool = False  # gemini-embedding-004 is free tier

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key: str = settings.api_key if settings else ""
        self._model: str = (
            settings.extra.get("gemini_model_embedding", _DEFAULT_MODEL)
            if settings
            else _DEFAULT_MODEL
        )

    # ------------------------------------------------------------------
    # available()
    # ------------------------------------------------------------------

    async def available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # call_structured() — embed()
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
        """Return an embedding vector wrapped as a dict.

        The primary interface is ``embed(text)`` — ``call_structured`` is
        provided to satisfy the ``LLMAdapter`` contract and returns:
        ``{"embedding": [...], "model": str, "dim": int}``.
        """
        vector = await self.embed(prompt)
        return {
            "embedding": vector.tolist(),
            "model": self._model,
            "dim": len(vector),
        }

    async def embed(self, text: str) -> Any:
        """Return the embedding ``numpy`` ndarray for *text*."""
        import numpy as _np

        if not self._api_key:
            raise ProviderError(
                "gemini_embedding: no API key (GEMINI_API_KEY missing)",
                retryable=False,
            )

        url = _EMBED_URL.format(model=self._model)
        body = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
        }

        try:
            raw = await self._post(url, body)
            return _parse_embed_response(raw)
        except ProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ProviderError(
                    f"gemini_embedding rate limited (429)", retryable=True
                ) from exc
            else:
                raise ProviderError(
                    f"gemini_embedding HTTP {status}: {exc}",
                    retryable=True,
                ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(
                f"gemini_embedding connection error: {exc}",
                retryable=True,
            ) from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                json=body,
                params={"key": self._api_key},
                timeout=60.0,
            )
            resp.raise_for_status()
        return resp.json()


def _parse_embed_response(raw: dict[str, Any]) -> Any:
    """Extract the embedding vector as a numpy array."""
    import numpy as _np

    try:
        values = raw["embedding"]["values"]
    except (KeyError, TypeError) as exc:
        raise ProviderError(
            f"gemini_embedding: unexpected response shape: {exc}. Raw: {raw!r:.200}",
            retryable=True,
        ) from exc
    return _np.array(values, dtype="float32")
