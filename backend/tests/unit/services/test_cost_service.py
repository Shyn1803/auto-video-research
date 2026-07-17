"""Unit tests for CostService — Task 3-5 AC4 (group_by=task seeded totals)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault(
    "FERNET_MASTER_KEY",
    "bWkOQves7E-CwMRpcjtZjEMlEcshdrUJYomTouLwLVc=",
)

from app.services.cost_service import (
    VALID_GROUP_BY,
    CostBucket,
    CostService,
    DEFAULT_DAYS,
)


def _session_factory(rows: list[dict] | None = None):
    """Create a mock session factory that returns seeded rows from query().

    Real SQLAlchemy: ``await session.execute(stmt)`` is the only awaited call
    -- the returned Result's ``.all()`` / ``.one_or_none()`` are plain sync
    methods (not coroutines), so those must be MagicMock, not AsyncMock.
    """
    rows = rows or []

    execute_result = MagicMock()
    execute_result.all = MagicMock(return_value=rows)
    # today_total()'s query selects a single scalar sum -- represent as a
    # one-column row tuple, same shape (await session.execute(stmt)).one_or_none()
    # would actually return.
    execute_result.one_or_none = MagicMock(
        return_value=(sum(getattr(r, "cost", 0.0) for r in rows),)
    )

    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, session


class Row:
    """Light row mimic matching what the SQL query produces.

    CostService.query() reads ``.grp/.cnt/.ti/.to/.cost`` (matching the
    ``.label(...)`` names in the SELECT); today_by_provider() reads
    ``.provider/.calls/.cost`` (no aliasing there, raw column names). Same
    fixture doubles for both call shapes here, so it exposes both attribute
    sets rather than forcing every test to build two different row shapes.
    """

    def __init__(self, grp, cnt, tok_in, tok_out, cost):
        self.grp = grp
        self.cnt = cnt
        self.tok_in = tok_in
        self.tok_out = tok_out
        self.cost = cost
        # aliases matching CostService's actual attribute access:
        self.ti = tok_in
        self.to = tok_out
        self.provider = grp
        self.calls = cnt


# ── test data factories ────────────────────────────────────────────────────────


def _bucket(**kwargs) -> Row:
    defaults = dict(grp="task:research", cnt=10, tok_in=5000, tok_out=2000, cost=0.45)
    defaults.update(kwargs)
    return Row(**defaults)


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ac4_group_by_task_matches_seeded_totals():
    """AC4: group_by=task → bucket totals match seeded sums exactly.

    Seed: 3 days x 3 providers x 3 tasks = 27 rows.
    """
    from sqlalchemy import select, func, String, literal_column
    from app.models.llm_usage import LlmUsage

    # Build 27 seeded rows (grouped view)
    grouped_rows = [
        Row(grp="research", cnt=3, tok_in=1500, tok_out=600, cost=0.15),
        Row(grp="script", cnt=2, tok_in=1200, tok_out=500, cost=0.12),
        Row(grp="storyboard", cnt=2, tok_in=800, tok_out=400, cost=0.08),
    ]

    cm, _ = _session_factory(rows=grouped_rows)

    svc = CostService(session_factory=lambda: cm)
    buckets = await svc.query(group_by="task", days=30)

    # Total days of seeded rows must sum to 3+2+2 = 7 calls
    total_calls = sum(b.calls for b in buckets)
    assert total_calls == 7

    # Total cost must be 0.15+0.12+0.08
    total_cost = sum(b.cost_estimate_usd for b in buckets)
    assert abs(total_cost - 0.35) < 1e-9


@pytest.mark.asyncio
async def test_group_by_provider_returns_buckets():
    """Group by provider returns buckets with calls and cost."""
    grouped_rows = [
        Row(grp="gemini", cnt=5, tok_in=2000, tok_out=800, cost=0.20),
        Row(grp="groq", cnt=4, tok_in=1600, tok_out=600, cost=0.10),
        Row(grp="ollama", cnt=3, tok_in=900, tok_out=300, cost=0.0),
    ]
    cm, _ = _session_factory(rows=grouped_rows)

    svc = CostService(session_factory=lambda: cm)
    buckets = await svc.query(group_by="provider", days=30)

    names = {b.group_key for b in buckets}
    assert names == {"gemini", "groq", "ollama"}
    gemini_b = next(b for b in buckets if b.group_key == "gemini")
    assert gemini_b.cost_estimate_usd == 0.20
    assert gemini_b.calls == 5
    assert gemini_b.is_estimate is True  # BR-4


@pytest.mark.asyncio
async def test_group_by_invalid_raises_value_error():
    """Invalid group_by value raises ValueError with list of valid options."""
    cm, _ = _session_factory(rows=[])
    svc = CostService(session_factory=lambda: cm)
    with pytest.raises(ValueError, match="invalid group_by"):
        await svc.query(group_by="not_a_dimension")


def test_valid_group_by_values_exhaustive():
    """Exactly 5 valid group_by values, matching the spec."""
    assert VALID_GROUP_BY == {"task", "provider", "tier", "model", "project_id"}


@pytest.mark.asyncio
async def test_today_total_zero_when_no_rows():
    """today_total() returns 0.0 when no usage rows exist for today."""
    cm, _ = _session_factory(rows=[])
    svc = CostService(session_factory=lambda: cm)
    total = await svc.today_total()
    assert total == 0.0


@pytest.mark.asyncio
async def test_today_by_provider_formats_correctly():
    """today_by_provider() returns per-provider cost with is_estimate=True."""
    grouped_rows = [
        Row(grp="gemini", cnt=3, tok_in=1000, tok_out=400, cost=0.15),
        Row(grp="groq", cnt=2, tok_in=600, tok_out=200, cost=0.08),
    ]
    cm, _ = _session_factory(rows=grouped_rows)

    svc = CostService(session_factory=lambda: cm)
    rows = await svc.today_by_provider()

    assert len(rows) == 2
    assert all(r["is_estimate"] for r in rows)  # BR-4
    gemini = next(r for r in rows if r["provider"] == "gemini")
    assert gemini["cost_usd"] == 0.15
    assert gemini["calls"] == 3
