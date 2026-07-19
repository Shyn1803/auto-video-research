"""Unit tests for CapGuardDrain — Task 3-5 BR-2 (node-boundary cost drain).

Covers:
  1. total_today() returns sum of today's usage from DB
  2. total_today() returns 0.0 when session_factory is None
  3. total_today() returns 0.0 on DB exception (graceful fallback)
  4. persist() writes records into llm_usage and returns row count
  5. persist() returns 0 when session_factory is None
  6. persist() returns 0 when records list is empty
  7. check_before_node() raises DailyCostCapExceeded when total >= cap
  8. check_before_node() passes when total is under cap
  9. check_before_node() is a no-op when cap <= 0 (free-only chain)
  10. _parse_ts() parses ISO timestamps correctly
  11. _parse_ts() returns now() on empty or invalid input
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.core.cap_guard import CapGuardDrain
from app.core.cost_exceptions import DailyCostCapExceeded


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_sf(session):
    """Wrap a mock session in a callable that returns an async CM yielding it."""

    class _CM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    return lambda: _CM()


def _make_execute_result(one_or_none_value=None, scalars_value=None, rowcount=0):
    r = MagicMock()
    r.one_or_none = MagicMock(return_value=one_or_none_value)
    r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=scalars_value or [])))
    r.rowcount = rowcount
    return r


# ── 1. total_today() returns sum of today's usage from DB ──────────────────────


@pytest.mark.asyncio
async def test_total_today_returns_db_sum():
    """total_today() queries llm_usage and returns the summed cost."""
    session = MagicMock()
    session.commit = AsyncMock()

    row = MagicMock()
    row.__getitem__ = lambda self, i: 4.75
    session.execute = AsyncMock(return_value=_make_execute_result(one_or_none_value=row))

    sf = _make_sf(session)

    with patch("app.core.cap_guard.get_settings"):
        guard = CapGuardDrain(session_factory=sf)
        total = await guard.total_today()

    assert total == pytest.approx(4.75)


# ── 2. total_today() returns 0.0 when session_factory is None ─────────────────


@pytest.mark.asyncio
async def test_total_today_returns_zero_without_session_factory():
    with patch("app.core.cap_guard.get_settings"):
        guard = CapGuardDrain(session_factory=None)
    total = await guard.total_today()
    assert total == pytest.approx(0.0)


# ── 3. total_today() returns 0.0 on DB exception ───────────────────────────────


@pytest.mark.asyncio
async def test_total_today_returns_zero_on_db_error(caplog):
    """When the DB query raises, total_today() logs and returns 0.0."""
    session = MagicMock()
    session.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
    sf = _make_sf(session)

    with patch("app.core.cap_guard.get_settings"):
        guard = CapGuardDrain(session_factory=sf)
        total = await guard.total_today()

    assert total == pytest.approx(0.0)
    # Warning was logged
    assert any("cap_guard.db_query_failed" in r.message for r in caplog.records)


# ── 4. persist() writes records and returns row count ──────────────────────────


@pytest.mark.asyncio
async def test_persist_writes_records_and_returns_count():
    """persist() batch-inserts LlmUsage rows and returns the number written."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    sf = _make_sf(session)

    records = [
        MagicMock(
            created_at="2026-07-19T10:00:00+00:00",
            provider_name="ollama",
            capability="research",
            tokens_used=1000,
            cost_estimate_usd=0.01,
            latency_ms=250,
            success=True,
        ),
        MagicMock(
            created_at="2026-07-19T11:00:00+00:00",
            provider_name="edge_tts",
            capability="tts",
            tokens_used=500,
            cost_estimate_usd=0.005,
            latency_ms=800,
            success=True,
        ),
    ]

    guard = CapGuardDrain(session_factory=sf)
    written = await guard.persist(records)
    assert written == 2
    assert session.add.call_count == 2
    session.commit.assert_called_once()


# ── 5. persist() returns 0 when session_factory is None ────────────────────────


@pytest.mark.asyncio
async def test_persist_returns_zero_without_session_factory():
    guard = CapGuardDrain(session_factory=None)
    result = await guard.persist([MagicMock()])
    assert result == 0


# ── 6. persist() returns 0 when records list is empty ──────────────────────────


@pytest.mark.asyncio
async def test_persist_returns_zero_on_empty_records():
    session = MagicMock()
    sf = _make_sf(session)
    guard = CapGuardDrain(session_factory=sf)
    result = await guard.persist([])
    assert result == 0
    session.commit.assert_not_called()


# ── 7. check_before_node() raises DailyCostCapExceeded when total >= cap ───────


@pytest.mark.asyncio
async def test_check_before_node_raises_on_breach():
    """When accumulated daily spending >= cap, check_before_node raises."""
    session = MagicMock()
    row = MagicMock()
    row.__getitem__ = lambda self, i: 5.0  # total_today returns 5.0
    session.execute = AsyncMock(return_value=_make_execute_result(one_or_none_value=row))
    sf = _make_sf(session)

    settings = MagicMock()
    settings.daily_cost_cap_usd = 4.0  # cap lower than today's total

    with patch("app.core.cap_guard.get_settings", return_value=settings):
        guard = CapGuardDrain(session_factory=sf)
        with pytest.raises(DailyCostCapExceeded) as exc_info:
            await guard.check_before_node()

    assert exc_info.value.current == pytest.approx(5.0)
    assert exc_info.value.limit == pytest.approx(4.0)
    assert exc_info.value.last_provider == "(node boundary)"


# ── 8. check_before_node() passes when total is under cap ──────────────────────


@pytest.mark.asyncio
async def test_check_before_node_passes_under_cap():
    session = MagicMock()
    row = MagicMock()
    row.__getitem__ = lambda self, i: 1.0
    session.execute = AsyncMock(return_value=_make_execute_result(one_or_none_value=row))
    sf = _make_sf(session)

    settings = MagicMock()
    settings.daily_cost_cap_usd = 10.0

    with patch("app.core.cap_guard.get_settings", return_value=settings):
        guard = CapGuardDrain(session_factory=sf)
        total = await guard.check_before_node()

    assert total == pytest.approx(1.0)


# ── 9. check_before_node() is a no-op when cap <= 0 ────────────────────────────


@pytest.mark.asyncio
async def test_check_before_node_noop_when_cap_zero():
    """cap=0 means free-only chain; payment gate filters paid providers out."""
    settings = MagicMock()
    settings.daily_cost_cap_usd = 0.0

    with patch("app.core.cap_guard.get_settings", return_value=settings):
        guard = CapGuardDrain(session_factory=None)
        total = await guard.check_before_node()

    assert total == pytest.approx(0.0)


# ── 10. _parse_ts() parses ISO timestamps correctly ────────────────────────────


def test_parse_ts_parses_iso_string():
    ts = "2026-07-19T14:30:00+00:00"
    result = CapGuardDrain._parse_ts(ts)
    assert result == datetime.fromisoformat(ts)


# ── 11. _parse_ts() returns now() on empty or invalid input ────────────────────


def test_parse_ts_returns_now_on_empty():
    guard = CapGuardDrain()
    now_before = datetime.now(UTC)
    result = guard._parse_ts("")
    now_after = datetime.now(UTC)
    assert now_before <= result <= now_after


def test_parse_ts_returns_now_on_garbage():
    guard = CapGuardDrain()
    now_before = datetime.now(UTC)
    result = guard._parse_ts("not-a-timestamp")
    now_after = datetime.now(UTC)
    assert now_before <= result <= now_after
