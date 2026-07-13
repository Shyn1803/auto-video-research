"""Router + failover + ALLOW_PAID gate -- Acceptance Criteria test suite.

One test per AC (AC1-AC4, BR-1, BR-5) plus circuit-breaker + usage logging checks.
All adapters are mock/fake: zero network calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from unittest.mock import patch

import pytest

from app.adapters.base import BaseAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm, get_adapter_class
from app.core.router import ProviderRouter, CACHE_TTL_S, CIRCUIT_BREAKER_S


# ── fake settings (no .env loading) ─────────────────────────────────────────

class FakeSettings:
    llm_chain: str = ""
    llm_chain_cheap: str = ""
    tts_chain: str = ""
    tts_chain_cheap: str = ""
    search_chain: str = ""
    allow_paid: bool = False

    def __getattr__(self, name: str) -> str:
        return ""


# ── mock adapters ────────────────────────────────────────────────────────────

@register_llm("always_ok")
class OkAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        return {"text": "ok", "tokens": max_tokens}


@register_llm("fail_retryable")
class FailRetryableAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        raise ProviderError("upstream 500", retryable=True)


@register_llm("fail_nonretryable")
class FailNonRetryableAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        raise ProviderError("invalid prompt", retryable=False)


@register_llm("timeout")
class TimeoutAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        raise TimeoutError("timed out")


@register_llm("health_boom")
class HealthBoomAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        raise RuntimeError("conn refused")

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        return {"text": "ok"}


@register_llm("paid")
class PaidAdapter(BaseAdapter):
    is_paid = True

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        return {"text": "paid", "tokens": max_tokens}


@register_llm("free")
class FreeAdapter(BaseAdapter):
    is_paid = False

    async def available(self) -> bool:
        return True

    async def call_structured(self, prompt, schema, *, temperature=0, max_tokens=2048):
        return {"text": "free", "tokens": max_tokens}


# ── helpers ──────────────────────────────────────────────────────────────────

def make_router(chain: str, *, allow_paid: bool = False) -> ProviderRouter:
    s = FakeSettings()
    s.llm_chain = chain
    s.allow_paid = allow_paid
    return ProviderRouter(settings=s)


# ── AC1: mock 500 → next provider answers + failover event ------------------

@pytest.mark.asyncio
async def test_happy_500_failover_to_next_provider():
    router = make_router("fail_retryable,always_ok")
    result = await router.call(
        "llm", "call_structured",
        args=("hi", {"type": "str"}),
        correlation_id="corr-1",
    )
    assert result["text"] == "ok"
    usage = router.pop_usage()
    assert len(usage) == 2
    assert usage[0].success is False
    assert usage[0].error_type == "ProviderError"
    assert usage[1].success is True


# ── AC2 / BR-2: 400 invalid → fail immediately, no failover ------------------

@pytest.mark.asyncio
async def test_400_nonretryable_fails_immediately():
    router = make_router("fail_nonretryable,always_ok")
    with pytest.raises(Exception) as exc_info:
        await router.call("llm", "call_structured", args=("hi", {"type": "str"}))
    from app.core.router import AllProvidersFailed
    assert isinstance(exc_info.value, AllProvidersFailed)
    # Only the non-retryable provider should be in failures; chain stops there
    assert len(exc_info.value.failures) == 1
    assert exc_info.value.failures[0].provider == "fail_nonretryable"
    usage = router.pop_usage()
    assert len(usage) == 1
    assert usage[0].success is False


# ── AC3 / BR-1: paid + ALLOW_PAID=false → never selected --------------------

@pytest.mark.asyncio
async def test_paid_adapter_blocked_when_allow_paid_false():
    router = make_router("paid,free", allow_paid=False)
    providers = router.available_providers("llm")
    names = [p.name for p in providers]
    assert "paid" not in names
    assert "free" in names


# ── AC4 / BR-3: all chain exhausted → AllProvidersFailed with per-provider reasons

@pytest.mark.asyncio
async def test_all_chain_exhausted_carries_all_reasons():
    # Both will fail; timeout is also retryable so loop continues to exhaustion
    router = make_router("fail_retryable,timeout")
    with pytest.raises(Exception) as exc_info:
        await router.call("llm", "call_structured", args=("hi", {"type": "str"}))
    from app.core.router import AllProvidersFailed
    assert isinstance(exc_info.value, AllProvidersFailed)
    # 2 failures attempted before exhaustion
    assert len(exc_info.value.failures) == 2
    providers_in = [f.provider for f in exc_info.value.failures]
    assert "fail_retryable" in providers_in
    assert "timeout" in providers_in
    usage = router.pop_usage()
    assert len(usage) == 2
    assert all(not u.success for u in usage)


# ── AC5 / BR-5: health fail → 60s circuit open → auto-retry → 1 event ------

@pytest.mark.asyncio
async def test_circuit_breaker_60s_exclusion_and_single_event(monkeypatch, caplog):
    router = make_router("health_boom,always_ok")

    fake_mono = [0.0]

    def _mono() -> float:
        return fake_mono[0]

    monkeypatch.setattr("app.core.router.time.monotonic", _mono)
    monkeypatch.setattr("app.core.router.CIRCUIT_BREAKER_S", 2.0)

    caplog.set_level(logging.INFO, logger="avr.router")

    # 1st call → health_boom raises → circuit trips
    with pytest.raises(Exception):
        await router.call("llm", "call_structured", args=("hi", {"type": "str"}))

    # window is open → health_boom excluded; always_ok is still selected
    providers = router.available_providers("llm")
    names = [p.name for p in providers]
    assert "health_boom" not in names
    assert "always_ok" in names

    # advance just past breaker window
    fake_mono[0] += 2.1

    # window should be closed → health_boom re-included (will fail again but is attempted)
    providers = router.available_providers("llm")
    names = [p.name for p in providers]
    assert "health_boom" in names

    # circuit_open event logged exactly once for the episode
    circuit_msgs = [
        r for r in caplog.records if "circuit_open" in r.getMessage()
    ]
    assert len(circuit_msgs) == 1


# ── extras: ALLOW_PAID=true → paid admitted; usage count correct -----------

@pytest.mark.asyncio
async def test_paid_admitted_when_allow_paid_true():
    router = make_router("paid,free", allow_paid=True)
    providers = router.available_providers("llm")
    names = [p.name for p in providers]
    assert "paid" in names


@pytest.mark.asyncio
async def test_usage_logged_only_on_attempts():
    router = make_router("fail_retryable,always_ok")
    await router.call("llm", "call_structured", args=("hi", {"type": "str"}))
    usage = router.pop_usage()
    assert len(usage) == 2
    assert usage[0].success is False
    assert usage[0].provider_name == "fail_retryable"
    assert usage[0].capability == "llm"
    assert usage[1].success is True
    assert usage[1].provider_name == "always_ok"


# ── extras: 30s availability cache is cached -------------------------------

@pytest.mark.asyncio
async def test_availability_is_cached(monkeypatch):
    router = make_router("always_ok")
    fake_mono = [0.0]

    def _mono() -> float:
        return fake_mono[0]

    monkeypatch.setattr("app.core.router.time.monotonic", _mono)
    monkeypatch.setattr("app.core.router.CACHE_TTL_S", 10.0)

    # populate cache via call
    await router.call("llm", "call_structured", args=("hi", {"type": "str"}))
    key = _cache_key("llm", "always_ok")
    entry = router._cache_get(key)
    assert entry is not None
    assert entry.available is True

    # bump time -- still within TTL, cache hit
    fake_mono[0] += 5.0
    assert router._cache_get(key) is not None

    # beyond TTL -- cache miss
    fake_mono[0] += 11.0
    assert router._cache_get(key) is None


# ── extras: TimeoutError treated as retryable failover ----------------------

@pytest.mark.asyncio
async def test_timeout_failover():
    router = make_router("timeout,always_ok")
    result = await router.call("llm", "call_structured", args=("hi", {"type": "str"}))
    assert result["text"] == "ok"
    usage = router.pop_usage()
    assert len(usage) == 2
    assert usage[0].error_type == "TimeoutError"
    assert usage[0].retryable is True
    assert usage[1].success is True