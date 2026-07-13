"""ProviderRouter -- chain resolution with failover, circuit breaker, ALLOW_PAID gate."""

from __future__ import annotations

import logging
import time
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.adapters.base import ProviderError, ProviderSettings, TTSAdapter
from app.adapters.registry import get_adapter_class
from app.core.exceptions import AllProvidersFailed, ProviderFailure

logger = logging.getLogger("avr.router")

# ---- capabilitiy types (extend as adapters are added) ----

_CAP: dict[str, type[ABC]] = {"llm": TTSAdapter}  # minimum for test; full set added later


# ---- tuning constants ----

CACHE_TTL_S: float = 30.0
CIRCUIT_BREAKER_S: float = 60.0


def _cache_key(capability: str, name: str) -> str:
    return f"{capability}:{name}"


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---- local structures (not imported from exceptions to keep router self-contained) ----

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
# Router
# ---------------------------------------------------------------------------

class ProviderRouter:
    """Routes capability calls through an env-declared provider chain."""

    def __init__(self, settings: Any | None = None) -> None:
        from app.core.config import get_settings as gs
        self._settings = settings or gs()
        self._availability: dict[str, AvailabilityEntry] = {}
        self._circuit_open_until: dict[str, float] = {}
        self._cb_event_sent: set[str] = set()
        self._usage: list[UsageRecord] = []

    # -- chain ---------------------------------------------------------

    def get_chain(self, capability: str, tier: str = "") -> list[str]:
        var = f"{capability.upper()}_CHAIN"
        if tier:
            var += f"_{tier.upper()}"
        raw = getattr(self._settings, var.lower(), "")
        return [p.strip() for p in raw.split(",") if p.strip()]

    # -- availability + circuit breaker ---------------------------------

    def _cache_get(self, key: str) -> AvailabilityEntry | None:
        entry = self._availability.get(key)
        if entry and (time.monotonic() - entry.last_check) < CACHE_TTL_S:
            return entry
        return None

    def _cache_set(self, key: str, entry: AvailabilityEntry) -> None:
        self._availability[key] = entry

    def _is_circuit_open(self, key: str) -> bool:
        until = self._circuit_open_until.get(key, 0.0)
        if time.monotonic() < until:
            return True
        self._circuit_open_until.pop(key, None)
        self._cb_event_sent.discard(key)
        return False

    def _paid_allowed(self, adapter: ABC) -> bool:
        allow = getattr(self._settings, "allow_paid", False)
        return not (getattr(adapter, "is_paid", True) and not allow)

    # -- public: resolve available providers ----------------------------

    def available_providers(self, capability: str, tier: str = "") -> list[ABC]:
        out: list[ABC] = []
        for name in self.get_chain(capability, tier):
            cls = get_adapter_class(capability, name)
            if cls is None:
                continue
            adapter: ABC = cls(ProviderSettings(provider_name=name))
            if not self._paid_allowed(adapter):
                continue
            key = _cache_key(capability, name)
            if self._is_circuit_open(key):
                continue
            out.append(adapter)
        return out

    # -- call with failover ---------------------------------------------

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
        providers = self.available_providers(capability, tier)
        if not providers:
            raise AllProvidersFailed(
                capability=capability,
                chain=[],
                failures=[
                    ProviderFailure(provider="<none>", reason="no available providers")
                ],
                correlation_id=correlation_id,
            )

        tried: list[ProviderFailure] = []
        loop_start = time.monotonic()

        for adapter in providers:
            name = getattr(adapter, "name", "")
            key = _cache_key(capability, name)
            try:
                fn: Callable[..., Any] = getattr(adapter, method)
                t0 = time.monotonic()
                result = await fn(*args, **kwargs)
                latency = (time.monotonic() - t0) * 1000
                self._cache_set(
                    key,
                    AvailabilityEntry(available=True, last_check=time.monotonic()),
                )
                self._usage.append(
                    UsageRecord(
                        provider_name=name,
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
                    provider=name, reason=str(exc), retryable=exc.retryable
                )
                tried.append(failure)
                self._usage.append(
                    UsageRecord(
                        provider_name=name,
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
                    raise AllProvidersFailed(
                        capability=capability,
                        chain=[p.name for p in providers],
                        failures=tried,
                        correlation_id=correlation_id,
                    ) from exc
                self._emit_failover(capability, name, str(exc), correlation_id)

            except (TimeoutError, OSError) as exc:
                latency = (time.monotonic() - loop_start) * 1000
                failure = ProviderFailure(provider=name, reason=str(exc), retryable=True)
                tried.append(failure)
                self._usage.append(
                    UsageRecord(
                        provider_name=name,
                        capability=capability,
                        success=False,
                        error_type=type(exc).__name__,
                        retryable=True,
                        latency_ms=latency,
                        created_at=_now_iso(),
                        correlation_id=correlation_id,
                    )
                )
                self._emit_failover(capability, name, str(exc), correlation_id)

        raise AllProvidersFailed(
            capability=capability,
            chain=[p.name for p in providers],
            failures=tried,
            correlation_id=correlation_id,
        )

    # -- health check --------------------------------------------------

    async def check_health(self, capability: str, provider_name: str) -> bool:
        cls = get_adapter_class(capability, provider_name)
        if cls is None:
            return False
        key = _cache_key(capability, provider_name)
        try:
            ok = await cls(ProviderSettings(provider_name=provider_name)).available()
        except Exception as exc:
            ok = False
            self._trip_circuit(capability, provider_name, str(exc))
        self._cache_set(
            key, AvailabilityEntry(available=ok, last_check=time.monotonic())
        )
        return ok

    async def refresh_all(self) -> None:
        seen: set[tuple[str, str]] = set()
        for cap in _CAP:
            for name in self.get_chain(cap):
                seen.add((cap, name))
            for name in self.get_chain(cap, "cheap"):
                seen.add((cap, name))
        for cap, name in seen:
            await self.check_health(cap, name)

    # -- circuit breaker ------------------------------------------------

    def _trip_circuit(self, capability: str, provider_name: str, reason: str) -> None:
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

    # -- events ---------------------------------------------------------

    def _emit_failover(
        self,
        capability: str,
        provider: str,
        reason: str,
        correlation_id: str,
    ) -> None:
        logger.info(
            "provider.failover capability=%s provider=%s reason=%s corr=%s",
            capability,
            provider,
            reason,
            correlation_id,
        )

    def _emit_exhausted(
        self,
        capability: str,
        chain: list[str],
        failures: list[ProviderFailure],
        correlation_id: str,
    ) -> None:
        logger.info(
            "provider.exhausted capability=%s chain=%s failures=%d corr=%s",
            capability,
            ",".join(chain),
            len(failures),
            correlation_id,
        )

    # -- usage readout --------------------------------------------------

    @property
    def usage(self) -> list[UsageRecord]:
        return list(self._usage)

    def pop_usage(self) -> list[UsageRecord]:
        recs = list(self._usage)
        self._usage.clear()
        return recs
