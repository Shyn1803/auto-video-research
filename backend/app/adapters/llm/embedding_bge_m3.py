"""BGE-M3 local embedding adapter (embedding_bge_m3).

Runs in-process in the backend v1 — no separate service (decision ⏳,
split to service only if bottleneck, per task 9-3).

Configuration arrives via ``ProviderSettings.extra`` (set by the router).
Accepts ``EMBEDDING_DEVICE=cpu|cuda`` for device selection.

All internal errors wrapped in ``ProviderError``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.bge_m3")

try:
    from sentence_transformers import SentenceTransformer

    _HAS_ST = True
except ImportError:
    _HAS_ST = False  # type: ignore[assignment]


@register_llm("bge_m3_local")
class BgeM3LocalLLM(LLMAdapter):
    """BGE-M3 embedding adapter — runs in-process, free, local."""

    name: str = "bge_m3_local"
    is_paid: bool = False

    # Class-level singleton so we load the model once per process.
    _instance: "BgeM3LocalLLM | None" = None

    # Default model name for sentence-transformers
    _DEFAULT_MODEL: str = "BAAI/bge-m3"

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._device: str = (
            self.settings.extra.get("embedding_device", "cpu")
            if settings
            else "cpu"
        )
        self._model_name: str = self._DEFAULT_MODEL
        self._model: Any = None  # lazy-loaded SentenceTransformer

    # ------------------------------------------------------------------
    # available()
    # ------------------------------------------------------------------

    async def available(self) -> bool:
        """Available when sentence-transformers is installed and importable.

        Re-checks importability live (rather than trusting only the
        module-import-time ``_HAS_ST`` flag) so that availability reflects the
        environment at call time — e.g. a test double injected into
        ``sys.modules`` after this module was first imported.
        """
        if _HAS_ST:
            return True
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            logger.warning(
                "bge_m3_local unavailable: sentence-transformers not installed. "
                "Install it with: pip install sentence-transformers"
            )
            return False
        return True

    # ------------------------------------------------------------------
    # call_structured() — implemented as embed()
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
        # For the embedding "LLM" we expose embed() separately;
        # call_structured delegates to it as a dict {"embedding": [...]}.
        emb = await self.embed(prompt)
        return {"embedding": emb.tolist(), "model": self._model_name, "dim": len(emb)}

    # ------------------------------------------------------------------
    # embed() — primary interface
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> Any:  # returns numpy ndarray
        """Return the BGE-M3 embedding vector for *text* (numpy ndarray)."""
        import numpy as _np  # local import to keep top-level clean

        try:
            model = self._get_model()
            # sentence-transformers is synchronous; run in threadpool
            import asyncio
            loop = asyncio.get_event_loop()
            emb = await loop.run_in_executor(
                None, lambda: model.encode(text, normalize_embeddings=True)
            )
            if emb is None:
                raise ProviderError(
                    "bge_m3_local: model.encode() returned None",
                    retryable=False,
                )
            result = _np.asarray(emb, dtype="float32")
            return result
        except ImportError as exc:
            raise ProviderError(
                f"bge_m3_local: sentence-transformers not installed — "
                f"pip install sentence-transformers ({exc})",
                retryable=False,
            ) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"bge_m3_local embed error: {exc}",
                retryable=True,
            ) from exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_model(self) -> Any:
        if not _HAS_ST:
            raise ProviderError(
                "bge_m3_local: sentence-transformers is not installed",
                retryable=False,
            )
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "bge_m3_local: loading model %r on device=%s …",
                    self._model_name,
                    self._device,
                )
                self._model = SentenceTransformer(
                    self._model_name, device=self._device
                )
                logger.info("bge_m3_local: model loaded")
            except Exception as exc:
                raise ProviderError(
                    f"bge_m3_local: failed to load model: {exc}",
                    retryable=False,
                ) from exc
        return self._model
