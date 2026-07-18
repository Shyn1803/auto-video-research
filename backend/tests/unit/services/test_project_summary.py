"""Unit tests for ProjectSummaryService — task 5-10.

Zero network: fake AsyncSession (same pattern as test_project_service.py).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.project_summary import ProjectSummaryService

PID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OWNER = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER = uuid.UUID("99999999-9999-9999-9999-999999999999")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _proj(owner_id=OWNER, pid=PID):
    p = MagicMock()
    p.id, p.owner_id = pid, owner_id
    p.name, p.topic, p.mode = "T", "AI", "interactive"
    p.status, p.language = "DRAFT", "vi"
    p.formats = "{vertical_1080x1920}"
    p.voice_id, p.voice_gender, p.cloned_from, p.archived_at = None, None, None, None
    p.created_at = p.updated_at = datetime.now(UTC)
    return p


def _u(cost):
    r = MagicMock()
    r.project_id, r.cost_estimate, r.success = str(PID), Decimal(str(cost)), True
    return r


STATS = _src = lambda **kw: _make_src(**kw)


def _make_src(total=0, trusted=0, pinned=0, disabled=0):
    r = MagicMock()
    r.total, r.trusted, r.pinned, r.disabled = total, trusted, pinned, disabled
    return r


class R:
    """Imitates a SQLAlchemy query result."""

    def __init__(self, one=None, many=None, scalar=None):
        self._one = one
        self._many = list(many or [])
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._one

    def one_or_none(self):
        return self._one

    def all(self):
        return list(self._many)

    def scalars(self):
        m = MagicMock()
        m.all.return_value = list(self._many)
        return m

    def scalar(self):
        return self._scalar


class _S:
    """FIFO session — one result per execute() call.

    get_summary runs 7 queries in this order:
      1. project, 2. verdict (all_rows), 3. cost (many), 4. source stats (one),
      5. activity (many), 6. scene_count (scalar), 7. ai_summary sv (one).
    """

    def __init__(self, rows):
        self._q = list(rows)
        self.flush = AsyncMock()
        self.add = MagicMock()

    async def execute(self, *a, **kw):
        return self._q.pop(0) if self._q else R()


def _q(p=None, v=None, c=None, s=None, a=None, n=0, sv=None):
    return [
        R(one=p if p is not None else _proj()),
        R(many=v if v is not None else []),
        R(many=c if c is not None else []),
        R(one=s if s is not None else _make_src()),
        R(many=a if a is not None else []),
        R(scalar=n),
        R(one=sv),
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cost_sum_is_exact():
    s = await ProjectSummaryService(_S(_q(c=[_u(0.015), _u(0.005)]))).get_summary(PID, OWNER)
    assert s.estimated_cost_usd == pytest.approx(0.020, abs=1e-9)
    assert s.estimated_cost_label == "ước tính"


@pytest.mark.asyncio
async def test_zero_cost():
    s = await ProjectSummaryService(_S(_q(c=[]))).get_summary(PID, OWNER)
    assert s.estimated_cost_usd == 0.0


@pytest.mark.asyncio
async def test_403_non_owner():
    s = await ProjectSummaryService(_S([R(one=None)])).get_summary(PID, OTHER)
    assert s is None


@pytest.mark.asyncio
async def test_scene_count():
    s = await ProjectSummaryService(_S(_q(n=5))).get_summary(PID, OWNER)
    assert s.scene_count == 5


@pytest.mark.asyncio
async def test_source_stats():
    s = await ProjectSummaryService(_S(_q(s=_make_src(total=7, trusted=4, pinned=1, disabled=0)))).get_summary(PID, OWNER)
    sc = s.source_count
    assert sc.total == 7
    assert sc.trusted == 4
    assert sc.pinned == 1
    assert sc.disabled == 0


@pytest.mark.asyncio
async def test_verdict_pass():
    s = await ProjectSummaryService(_S(_q(v=[("PASS",)]))).get_summary(PID, OWNER)
    assert s.overall_verdict == "PASS"


@pytest.mark.asyncio
async def test_verdict_fail():
    s = await ProjectSummaryService(_S(_q(v=[("FAIL",)]))).get_summary(PID, OWNER)
    assert s.overall_verdict == "FAIL"


@pytest.mark.asyncio
async def test_verdict_none():
    s = await ProjectSummaryService(_S(_q(v=[]))).get_summary(PID, OWNER)
    assert s.overall_verdict is None


@pytest.mark.asyncio
async def test_verdict_warn():
    s = await ProjectSummaryService(_S(_q(v=[("WARN",)]))).get_summary(PID, OWNER)
    assert s.overall_verdict == "WARN"


@pytest.mark.asyncio
async def test_ai_summary_from_sv():
    sv_ = MagicMock()
    sv_.content = {"ai_summary": "Tóm tắt AI.", "sources": []}
    s = await ProjectSummaryService(_S(_q(sv=sv_))).get_summary(PID, OWNER)
    assert s.ai_summary == "Tóm tắt AI."


@pytest.mark.asyncio
async def test_ai_summary_none_no_key():
    sv_ = MagicMock()
    sv_.content = {"sources": []}
    s = await ProjectSummaryService(_S(_q(sv=sv_))).get_summary(PID, OWNER)
    assert s.ai_summary is None


@pytest.mark.asyncio
async def test_ai_summary_none_no_sv():
    s = await ProjectSummaryService(_S(_q(sv=None))).get_summary(PID, OWNER)
    assert s.ai_summary is None
