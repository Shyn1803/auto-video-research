"""ProviderRouter -- chain resolution with failover, circuit breaker, ALLOW_PAID gate.

Implements one-pass chain walk with:
  - *_CHAIN env resolution per capability/tier
  - 30-second availability cache
  - ALLOW_PAID gate at router (BR-1: never trust adapter alone)
  - Failover: retryable -> next provider; non-retryable 4xx -> fail immediately (BR-2)
  - Single-pass only -- never loop back to a tried provider (BR-4)
  - 60-second circuit breaker on health-check failure, event once per episode (BR-5)
  - AllProvidersFailed with per-provider reason list (BR-3)
  - Usage logging at router (never in adapter -- rules/logging.md)
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.adapters.base import BaseAdapter, ProviderError, ProviderSettings
from app.adapters.registry import get_adapter_class, get_registered
from app.core.exceptions import AllProvidersFailed, ProviderFailure

logger = logging.getLogger("avr.router")

# Re-export for test convenience (tests import these from app.core.router)
AllProvidersFailed = AllProvidersFailed  # noqa: F811 — re-export
ProviderFailure = ProviderFailure        # noqa: F811 — re-export

__all__ = [
    "ProviderRouter",
    "AvailabilityEntry",
    "UsageRecord",
    "CACHE_TTL_S",
    "CIRCUIT_BREAKER_S",
    "AllProvidersFailed",
    "ProviderFailure",
    "SUBJECT_FAILOVER",
    "SUBJECT_EXHAUSTED",
]

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

CACHE_TTL_S: float = 30.0
CIRCUIT_BREAKER_S: float = 60.0

# ---------------------------------------------------------------------------
# Event subjects (bus subjects, not event_type strings)
# ---------------------------------------------------------------------------

SUBJECT_FAILOVER = "provider.failover"
SUBJECT_EXHAUSTED = "provider.exhausted"

# ---------------------------------------------------------------------------
# Local data structures
# ---------------------------------------------------------------------------


@dataclass
class AvailabilityEntry:
    available: bool = False
    last_check: float = 0.0
    reason: str = ""


@dataclass
class UsageRecord:
    provider_name: str = ""
    capability: str = ""
    success: bool = False
    error_type: str | None = None
    retryable: bool = False
    tokens_used: int = 0
    cost_estimate_usd: float = 0.0
    latency_ms: float = 0.0
    created_at: str = ""
    correlation_id: str = ""


# ---------------------------------------------------------------------------
# Adapter loader
# ---------------------------------------------------------------------------


def _load_adapter(
    capability: str, name: str
) -> BaseAdapter | None:
    """Instantiate an adapter with ProviderSettings carrying capability-specific config."""
    from app.core.config import get_settings

    settings = get_settings()
    cls = get_adapter_class(capability, name)
    if cls is None:
        return None
    extra: dict[str, str] = {}
    if capability == "llm":
        extra["ollama_url"] = settings.ollama_url
        extra["model_cheap"] = settings.ollama_model_cheap
        extra["model_strong"] = settings.ollama_model_strong
        extra["gemini_model"] = settings.gemini_model
        extra["groq_model"] = settings.groq_model
        extra["openrouter_paid_model"] = settings.openrouter_paid_model
    elif capability == "tts":
        extra["tts_voice_female"] = settings.tts_voice_female
        extra["tts_voice_male"] = settings.tts_voice_male
        extra["tts_local_model"] = settings.tts_local_model
    elif capability == "search":
        extra["searxng_url"] = settings.searxng_url
        extra["tavily_api_key"] = settings.tavily_api_key
        extra["brave_api_key"] = settings.brave_api_key
        extra["serpapi_key"] = settings.serpapi_key
    elif capability == "image_gen":
        extra["sd_url"] = settings.sd_url
        extra["sd_model"] = settings.sd_model
        extra["embedding_device"] = settings.embedding_device
    elif capability == "asset_stock":
        extra["pexels_api_key"] = settings.pexels_api_key
        extra["pixabay_api_key"] = settings.pixabay_api_key
        extra["unsplash_access_key"] = settings.unsplash_access_key
    elif capability == "storage":
        extra["minio_url"] = settings.minio_url
        extra["minio_access_key"] = settings.minio_access_key
        extra["minio_secret_key"] = settings.minio_secret_key
        extra["bucket"] = settings.s3_bucket
        extra["aws_region"] = settings.aws_region
    elif capability == "publish":
        extra["youtube_client_id"] = settings.youtube_client_id
        extra["youtube_client_secret"] = settings.youtube_client_secret
        extra["tiktok_client_key"] = settings.tiktok_client_key
    return cls(
        ProviderSettings(provider_name=name, api_key="", base_url="", extra=extra)
    )


# ---------------------------------------------------------------------------
# ProviderRouter
# ---------------------------------------------------------------------------


class ProviderRouter:
    """Resolves an env-declared provider chain and walks it with failover."""

    def __init__(self) -> None:
        from app.core.config import get_settings

        self._settings = get_settings()
        self._availability: dict[str, AvailabilityEntry] = {}
        self._circuit_open_until: dict[str, float] = {}
        self._cb_event_sent: set[str] = set()
        self._usage: list[UsageRecord] = []

    # ------------------------------------------------------------------ #
    # Chain resolution (Step 1)
    # ------------------------------------------------------------------ #

    def get_chain(self, capability: str, tier: str = "") -> list[str]:
        """Return ordered provider names for *capability*/*tier* from env config.

        Maps ``{CAPABILITY_UPPER}_CHAIN`` (or ``{CAPABILITY_UPPER}_CHAIN_{TIER}``)
        to a clean list. Field names are snake_case in Settings (e.g. ``llm_chain_cheap``).
        """
        var = f"{capability.upper()}_CHAIN"
        if tier:
            var += f"_{tier.upper()}"
        field_name = var.lower()
        raw: str = getattr(self._settings, field_name, "")
        return [p.strip() for p in raw.split(",") if p.strip()]

    # ------------------------------------------------------------------ #
    # Availability cache (Step 2)
    # ------------------------------------------------------------------ #

    def _cache_get(self, key: str) -> AvailabilityEntry | None:
        entry = self._availability.get(key)
        if entry and (time.monotonic() - entry.last_check) < CACHE_TTL_S:
            return entry
        return None

    def _cache_set(self, key: str, entry: AvailabilityEntry) -> None:
        self._availability[key] = entry

    def _is_circuit_open(self, key: str) -> bool:
        """Return True if circuit breaker is still holding this provider out (BR-5)."""
        until = self._circuit_open_until.get(key, 0.0)
        if time.monotonic() < until:
            return True
        self._circuit_open_until.pop(key, None)
        self._cb_event_sent.discard(key)
        return False

    def _paid_allowed(self, adapter: BaseAdapter) -> bool:
        """BR-1: ALLOW_PAID gate enforced at router, never trust adapter alone."""
        allow = getattr(self._settings, "allow_paid", False)
        is_paid = getattr(adapter, "is_paid", True)
        return not (is_paid and not allow)

    # ------------------------------------------------------------------ #
    # Public: resolve ordered list of usable adapter instances
    # ------------------------------------------------------------------ #

    def available_providers(self, capability: str, tier: str = "") -> list[BaseAdapter]:
        """Return adapters passing all three gates:

        1. Registered in adapter registry
        2. Not filtered by ALLOW_PAID gate (BR-1)
        3. Not blocked by circuit breaker (BR-5)
        """
        out: list[BaseAdapter] = []
        seen_cls: set[type[BaseAdapter]] = set()
        for name in self.get_chain(capability, tier):
            cls = get_adapter_class(capability, name)
            if cls is None:
                logger.warning(
                    "registry miss: capability=%s name=%r -> skip", capability, name
                )
                continue
            # Deduplicate: same class may be registered under multiple aliases
            if cls in seen_cls:
                continue
            seen_cls.add(cls)
            adapter = _load_adapter(capability, name)
            if adapter is None:
                continue
            if not self._paid_allowed(adapter):
                continue
            key = _cache_key(capability, name)
            if self._is_circuit_open(key):
                continue
            out.append(adapter)
        return out

    # ------------------------------------------------------------------ #
    # Call with failover (Steps 3, 4)
    # ------------------------------------------------------------------ #

    async def call(
        self,
        capability: str,
        method: str,
        *,
        tier: str = "",
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        correlation_id: str = "",
    ) -> Any:
        """Call *method* on the first available adapter in the chain.

        Walks exactly one pass (BR-4). Per-provider behavior:
        - Non-retryable 4xx (BR-2) : raise AllProvidersFailed immediately, no failover
        - Retryable 5xx/Timeout/OS : emit failover event, try next
        - Chain exhausted (BR-3): raise AllProvidersFailed with per-provider reasons
        """
        providers = self.available_providers(capability, tier)
        if not providers:
            blocked_paid = []
            allow = getattr(self._settings, "allow_paid", False)
            if not allow:
                for name in get_registered(capability):
                    a = _load_adapter(capability, name)
                    if a and a.is_paid:
                        blocked_paid.append(name)
            raise AllProvidersFailed(
                capability=capability,
                chain=[],
                failures=[
                    ProviderFailure(
                        provider="<none>",
                        reason=(
                            "no available providers"
                            + (f"; paid blocked: {blocked_paid}" if blocked_paid else "")
                        ),
                    )
                ],
                correlation_id=correlation_id,
            )

        tried: list[ProviderFailure] = []
        loop_start = time.monotonic()

        for idx, adapter in enumerate(providers):
            provider_name = getattr(adapter, "name", "")
            key = _cache_key(capability, provider_name)
            to_provider = (
                providers[idx + 1].name if idx + 1 < len(providers) else "<none>"
            )
            try:
                fn: Callable[..., Any] = getattr(adapter, method)
                t0 = time.monotonic()
                result = await fn(*args, **(kwargs or {}))
                latency = (time.monotonic() - t0) * 1000
                self._cache_set(
                    key,
                    AvailabilityEntry(
                        available=True, last_check=time.monotonic()
                    ),
                )
                self._usage.append(
                    UsageRecord(
                        provider_name=provider_name,
                        capability=capability,
                        success=True,
                        latency_ms=latency,
                        created_at=_now_iso(),
                        correlation_id=correlation_id,
                    )
                )
                return result

            except ProviderError as exc:
                latency = (time.monotonic() - loop_start) * 1000
                failure = ProviderFailure(
                    provider=provider_name,
                    reason=str(exc),
                    retryable=exc.retryable,
                )
                tried.append(failure)
                self._usage.append(
                    UsageRecord(
                        provider_name=provider_name,
                        capability=capability,
                        success=False,
                        error_type="ProviderError",
                        retryable=exc.retryable,
                        latency_ms=latency,
                        created_at=_now_iso(),
                        correlation_id=correlation_id,
                    )
                )
                if not exc.retryable:
                    # BR-2: non-retryable 4xx -- fail immediately, no failover
                    raise AllProvidersFailed(
                        capability=capability,
                        chain=[p.name for p in providers],
                        failures=tried,
                        correlation_id=correlation_id,
                    ) from exc
                # Retryable -- emit failover event, continue to next provider
                await self._publish_failover(
                    capability=capability,
                    from_provider=provider_name,
                    to_provider=to_provider,
                    reason=str(exc),
                    correlation_id=correlation_id,
                )

            except (TimeoutError, OSError) as exc:
                latency = (time.monotonic() - loop_start) * 1000
                failure = ProviderFailure(
                    provider=provider_name, reason=str(exc), retryable=True
                )
                tried.append(failure)
                self._usage.append(
                    UsageRecord(
                        provider_name=provider_name,
                        capability=capability,
                        success=False,
                        error_type=type(exc).__name__,
                        retryable=True,
                        latency_ms=latency,
                        created_at=_now_iso(),
                        correlation_id=correlation_id,
                    )
                )
                # Trip circuit (infrastructure failure) + failover event
                self._trip_circuit(capability, provider_name, str(exc))
                await self._publish_failover(
                    capability=capability,
                    from_provider=provider_name,
                    to_provider=to_provider,
                    reason=str(exc),
                    correlation_id=correlation_id,
                )

            except Exception as exc:
                # Catch-all unexpected error -- treat as retryable
                latency = (time.monotonic() - loop_start) * 1000
                failure = ProviderFailure(
                    provider=provider_name, reason=str(exc), retryable=True
                )
                tried.append(failure)
                self._usage.append(
                    UsageRecord(
                        provider_name=provider_name,
                        capability=capability,
                        success=False,
                        error_type=type(exc).__name__,
                        retryable=True,
                        latency_ms=latency,
                        created_at=_now_iso(),
                        correlation_id=correlation_id,
                    )
                )
                self._trip_circuit(capability, provider_name, str(exc))
                await self._publish_failover(
                    capability=capability,
                    from_provider=provider_name,
                    to_provider=to_provider,
                    reason=str(exc),
                    correlation_id=correlation_id,
                )

        # Chain exhausted (BR-3)
        await self._publish_exhausted(
            capability=capability,
            chain=[p.name for p in providers],
            failures=tried,
            correlation_id=correlation_id,
        )
        raise AllProvidersFailed(
            capability=capability,
            chain=[p.name for p in providers],
            failures=tried,
            correlation_id=correlation_id,
        )

    # ------------------------------------------------------------------ #
    # Health check (Step 7)
    # ------------------------------------------------------------------ #

    async def check_health(self, capability: str, provider_name: str) -> bool:
        """On-demand health check for a single provider.

        Updates availability cache and trips circuit breaker on failure.
        """
        adapter = _load_adapter(capability, provider_name)
        if adapter is None:
            return False
        key = _cache_key(capability, provider_name)
        try:
            ok = await adapter.available()
        except Exception as exc:
            ok = False
            self._trip_circuit(capability, provider_name, str(exc))
            self._cache_set(
                key,
                AvailabilityEntry(
                    available=False,
                    last_check=time.monotonic(),
                    reason=str(exc),
                ),
            )
            return False
        self._cache_set(
            key,
            AvailabilityEntry(available=ok, last_check=time.monotonic()),
        )
        return ok

    async def refresh_all(self) -> None:
        """Periodic health refresh -- iterate all known capabilities."""
        known_caps = [
            "llm",
            "tts",
            "search",
            "image_gen",
            "asset_stock",
            "storage",
            "publish",
        ]
        seen: set[tuple[str, str]] = set()
        for cap in known_caps:
            for name in self.get_chain(cap):
                seen.add((cap, name))
            for name in self.get_chain(cap, "cheap"):
                seen.add((cap, name))
        tasks = [self.check_health(cap, name) for cap, name in seen]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ------------------------------------------------------------------ #
    # Circuit breaker (BR-5)
    # ------------------------------------------------------------------ #

    def _trip_circuit(self, capability: str, provider_name: str, reason: str) -> None:
        """Open circuit for 60s. Event emitted exactly once per episode."""
        key = _cache_key(capability, provider_name)
        self._circuit_open_until[key] = time.monotonic() + CIRCUIT_BREAKER_S
        if key not in self._cb_event_sent:
            self._cb_event_sent.add(key)
            logger.info(
                "provider.circuit_open capability=%s provider=%s reason=%s ttl=%ds",
                capability,
                provider_name,
                reason,
                int(CIRCUIT_BREAKER_S),
            )

    # ------------------------------------------------------------------ #
    # Event emission (Step 6) -- bus-backed, fallback to log
    # ------------------------------------------------------------------ #

    async def _publish_failover(
        self,
        *,
        capability: str,
        from_provider: str,
        to_provider: str,
        reason: str,
        correlation_id: str,
    ) -> None:
        """Emit ``provider.failover`` on the bus. Fire-and-forget."""
        payload = {
            "capability": capability,
            "from_provider": from_provider,
            "to_provider": to_provider,
            "reason": reason,
        }
        try:
            from app.events.bus import publish as _bus_publish

            await _bus_publish(SUBJECT_FAILOVER, payload)
        except Exception:
            logger.info(
                "provider.failover capability=%s from=%s to=%s reason=%s corr=%s",
                capability,
                from_provider,
                to_provider,
                reason,
                correlation_id,
            )

    async def _publish_exhausted(
        self,
        *,
        capability: str,
        chain: list[str],
        failures: list[ProviderFailure],
        correlation_id: str,
    ) -> None:
        """Emit ``provider.exhausted`` on the bus. Fire-and-forget."""
        payload = {
            "capability": capability,
            "chain": chain,
            "failures": [
                {
                    "provider": f.provider,
                    "reason": f.reason,
                    "retryable": f.retryable,
                }
                for f in failures
            ],
            "correlation_id": correlation_id,
        }
        try:
            from app.events.bus import publish as _bus_publish

            await _bus_publish(SUBJECT_EXHAUSTED, payload)
        except Exception:
            logger.info(
                "provider.exhausted capability=%s chain=%s failures=%d corr=%s",
                capability,
                ",".join(chain),
                len(failures),
                correlation_id,
            )

    # ------------------------------------------------------------------ #
    # Usage readout (Step 4)
    # ------------------------------------------------------------------ #

    @property
    def usage(self) -> list[UsageRecord]:
        return list(self._usage)

    def pop_usage(self) -> list[UsageRecord]:
        """Drain and return accumulated usage records."""
        recs = list(self._usage)
        self._usage.clear()
        return recs
