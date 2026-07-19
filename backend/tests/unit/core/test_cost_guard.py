"""Unit tests for CostGuard — Task 3-5 BR-1 / BR-2 (daily cap pre-call check).

Covers:
  1. before_call raises DailyCostCapExceeded when cap would be breached
  2. before_call passes when cost stays under cap
  3. before_call is a no-op when cap <= 0 (free-only chain)
  4. record() accumulates cost after a successful call
  5. reset() zeroes the in-memory accumulator
  6. current_spend() returns accumulated total
  7. today_cost_from_db() queries DB when session_factory provided
  8. before_call uses correlation_id in log context (smoke-test)
  9. record() then before_call correctly gate on accumulated spend
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cost_exceptions import DailyCostCapExceeded
from app.services.cost_guard import CostGuard


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_guard(*, cap: float = 10.0, session_factory=None, usage_records=None):
    """Build a CostGuard with a controlled daily_cost_cap setting."""
    settings = MagicMock()
    settings.daily_cost_cap_usd = cap
    with patch("app.services.cost_guard.get_settings", return_value=settings):
        return CostGuard(
            session_factory=session_factory,
            usage_records=usage_records,
        )


# ── 1. before_call raises when cap would be breached ───────────────────────────


@pytest.mark.asyncio
async def test_before_call_raises_on_cap_breach():
    guard = _make_guard(cap=1.0)
    guard._accumulated = 0.8
    with pytest.raises(DailyCostCapExceeded) as exc_info:
        await guard.before_call(0.5, "openai", "corr-1")
    assert exc_info.value.current == pytest.approx(1.3)
    assert exc_info.value.limit == 1.0
    assert exc_info.value.last_provider == "openai"


# ── 2. before_call passes when cost stays under cap ────────────────────────────


@pytest.mark.asyncio
async def test_before_call_passes_under_cap():
    guard = _make_guard(cap=5.0)
    guard._accumulated = 1.0
    # Should NOT raise when estimate fits
    await guard.before_call(2.0, "gemini", "corr-2")
    assert guard.current_spend() == pytest.approx(1.0)


# ── 3. before_call is a no-op when cap <= 0 (free-only chain) ─────────────────


@pytest.mark.asyncio
async def test_before_call_noop_when_cap_zero():
    guard = _make_guard(cap=0.0)
    guard._accumulated = 50.0  # pretend heavy prior usage
    # Should NOT raise — zero cap means "free only", payment gate filters paid
    await guard.before_call(10.0, "ollama", "corr-3")
    assert guard.current_spend() == pytest.approx(50.0)


# ── 4. record() accumulates cost after successful call ─────────────────────────


def test_record_accumulates_cost():
    guard = _make_guard(cap=10.0)
    guard.record(0.25)
    assert guard.current_spend() == pytest.approx(0.25)
    guard.record(0.75)
    assert guard.current_spend() == pytest.approx(1.0)


# ── 5. reset() zeroes the in-memory accumulator ────────────────────────────────


def test_reset_zeroes_accumulator():
    guard = _make_guard(cap=10.0)
    guard.record(3.5)
    assert guard.current_spend() == pytest.approx(3.5)
    guard.reset()
    assert guard.current_spend() == pytest.approx(0.0)


# ── 6. current_spend() returns accumulated total ───────────────────────────────


def test_current_spend_returns_accumulated():
    guard = _make_guard(cap=10.0)
    assert guard.current_spend() == pytest.approx(0.0)
    guard.record(2.0)
    guard.record(3.0)
    assert guard.current_spend() == pytest.approx(5.0)


# ── 7. today_cost_from_db() queries DB when session_factory provided ───────────


@pytest.mark.asyncio
async def test_today_cost_from_db_queries_session():
    sf = MagicMock()
    session = MagicMock()
    sf.return_value = session

    # session.execute returns a result whose scalar_one_or_none returns a row
    row = MagicMock()
    row.__getitem__ = lambda self, i: 7.5
    execute_result = MagicMock()
    execute_result.one_or_none.return_value = row
    session.execute = AsyncMock(return_value=execute_result)

    guard = _make_guard(cap=10.0, session_factory=sf)
    total = await guard.today_cost_from_db()
    assert total == pytest.approx(7.5)
    assert guard.current_spend() == pytest.approx(7.5)


@pytest.mark.asyncio
async def test_today_cost_from_db_returns_zero_when_no_session_factory():
    guard = _make_guard(cap=10.0, session_factory=None)
    total = await guard.today_cost_from_db()
    assert total == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_today_cost_from_db_returns_zero_on_db_error():
    sf = MagicMock()
    sf.return_value = AsyncMock()
    # Make session.execute raise
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    sf.side_effect = [session]

    guard = _make_guard(cap=10.0)
    # Monkey-patch to provide the session factory directly
    guard._session_factory = sf
    guard._accumulated = 0.0
    total = await guard.today_cost_from_db()
    assert total == pytest.approx(0.0)


# ── 8. before_call uses provider_name in exception and log context ─────────────
# (smoke-test — we verify the exception carries the right provider field)


@pytest.mark.asyncio
async def test_before_call_exception_includes_provider_name():
    guard = _make_guard(cap=1.0)
    guard._accumulated = 0.9
    with pytest.raises(DailyCostCapExceeded) as exc_info:
        await guard.before_call(0.3, "groq", "corr-4")
    assert "groq" in str(exc_info.value)


# ── 9. record() then before_call gates on accumulated spend ────────────────────


@pytest.mark.asyncio
async def test_record_then_before_call_gates_correctly():
    guard = _make_guard(cap=2.0)
    # First call under cap
    guard.record(1.0)
    await guard.before_call(0.5, "openrouter", "corr-5")
    # Second call at boundary — still under
    guard.record(0.5)
    await guard.before_call(0.0, "openrouter", "corr-5")
    # Third call breaches — cap is 2.0, accumulated is 1.5, +0.6 = 2.1 > 2.0
    guard.record(0.0)
    with pytest.raises(DailyCostCapExceeded):
        await guard.before_call(0.6, "openrouter", "corr-5")


# ── 10. before_call accepts zero estimate without reducing room ────────────────


@pytest.mark.asyncio
async def test_before_call_zero_estimate_never_raises():
    guard = _make_guard(cap=1.0)
    guard._accumulated = 0.99
    await guard.before_call(0.0, "ollama", "corr-6")
    assert guard.current_spend() == pytest.approx(0.99)
