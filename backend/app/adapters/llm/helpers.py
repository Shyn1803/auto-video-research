"""Shared helpers for LLM adapters.

- ``structured_call_helper``: wraps a low-level ``raw_call`` to produce
  structured JSON with automatic retry on parse failure (BR-1: up to 2
  retries = 3 total attempts; on 3rd failure raise non-retryable with raw
  output attached to the debug log, never swallowed).
- ``load_pricing`` / ``estimate_cost``: reads tokens + cost from
  ``pricing.yaml``; free providers record ``cost=0`` but the router still
  logs token counts for quota tracking (BR-3).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

import yaml

from app.adapters.base import ProviderError

logger = logging.getLogger("avr.llm.helpers")

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Pricing data
# ---------------------------------------------------------------------------

_PRICING_PATH: Path = (
    Path(__file__).resolve().parents[2] / "config" / "pricing.yaml"
)

_pricing_cache: dict[str, dict[str, Any]] | None = None


def load_pricing() -> dict[str, dict[str, Any]]:
    """Load and cache the pricing table from ``pricing.yaml``.

    Returns ``{provider_name: {model: {input_per_1k, output_per_1k, ...}}}``
    """
    global _pricing_cache
    if _pricing_cache is None:
        if not _PRICING_PATH.exists():
            logger.warning("pricing.yaml not found at %s — returning empty table", _PRICING_PATH)
            _pricing_cache = {}
        else:
            with _PRICING_PATH.open("r", encoding="utf-8") as f:
                _pricing_cache = yaml.safe_load(f) or {}
    return dict(_pricing_cache)


def estimate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """Return the USD cost estimate for a single call.

    Free providers return ``0.0`` (but token counts are still recorded
    by the router for quota tracking — BR-3).
    """
    table = load_pricing()
    provider_table = table.get(provider, {})
    model_table = provider_table.get(model, {})
    if not model_table:
        return 0.0
    input_cost = (input_tokens / 1000.0) * float(model_table.get("input_per_1k_usd", 0))
    output_cost = (output_tokens / 1000.0) * float(model_table.get("output_per_1k_usd", 0))
    return round(input_cost + output_cost, 6)


# ---------------------------------------------------------------------------
# Structured call with retry on parse failure (BR-1)
# ---------------------------------------------------------------------------


async def structured_call_helper(
    *,
    raw_call: Callable[[], Awaitable[str]],
    schema: dict[str, object],
    prompt_snippet: str,
    max_attempts: int = 3,
) -> dict[str, object]:
    """Call *raw_call*, parse its JSON response, and retry up to *max_attempts*
    on JSON parse failure.

    On the final (3rd) failure the raw output is logged at DEBUG level and a
    non-retryable ``ProviderError`` is raised — never swallowed.
    """
    last_raw: str | None = None
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            raw_text = await raw_call()
            last_raw = raw_text
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.debug(
                "structured_call parse error [attempt %d/%d] prompt=%r err=%s raw=%s",
                attempt,
                max_attempts,
                prompt_snippet[:80],
                exc,
                raw_text[:300],
            )
            if attempt == max_attempts:
                # BR-1 final failure: log raw output, raise non-retryable.
                logger.error(
                    "structured_call failed after %d attempts prompt=%r last_raw=%s",
                    max_attempts,
                    prompt_snippet[:100],
                    last_raw[:500] if last_raw else "<none>",
                )
                raise ProviderError(
                    f"structured_call: failed to parse JSON after {max_attempts} attempts "
                    f"(last error: {exc}). Raw output logged at DEBUG.",
                    retryable=False,
                ) from exc
        except Exception as exc:
            # Non-parse errors propagate immediately — no retry.
            raise ProviderError(
                f"structured_call: {exc}",
                retryable=False,
            ) from exc

    # Should not reach here, but satisfy mypy.
    assert last_error is not None
    raise ProviderError(
        f"structured_call: unexpected exit retryable=False after {max_attempts} attempts",
        retryable=False,
    ) from last_error


# ---------------------------------------------------------------------------
# Context manager for environment overrides in tests
# ---------------------------------------------------------------------------


class _OverrideEnv:
    """Temporarily override ``os.environ`` in a ``with`` block."""

    def __init__(self, overrides: dict[str, str]) -> None:
        self._overrides = overrides
        self._previous: dict[str, str | None] = {}

    def __enter__(self) -> "_OverrideEnv":
        import os as _os

        for k, v in self._overrides.items():
            self._previous[k] = _os.environ.get(k)
            _os.environ[k] = v
        return self

    def __exit__(self, *exc: Any) -> None:
        import os as _os

        for k, prev in self._previous.items():
            if prev is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = prev
