"""Unit tests -- Task 4-5 Step 8 (manual edit lineage + sub-step approvals, AC5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.step_approval_service import StepApprovalService
from app.services.versioning_service import VersioningService


def _sv(step, version, *, stale=False, content=None):
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.step = step
    sv.version = version
    sv.stale = stale
    sv.content = content or {}
    sv.created_by = "ai"
    sv.created_at = datetime.now(UTC)
    return sv


class _FakeResult:
    def __init__(self, rows=None, one=None):
        self._rows = rows if rows is not None else ([one] if one is not None else [])
        self._one = one

    def scalars(self):
        m = MagicMock()
        m.all.return_value = self._rows
        return m

    def scalar_one_or_none(self):
        if self._one is not None:
            return self._one
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, *results):
        self._queue = list(results)
        self.flush = AsyncMock()
        self.add = MagicMock()

    async def execute(self, stmt, *a, **kw):
        return self._queue.pop(0) if self._queue else _FakeResult()


# ── manual_edit() -- AC5 cross-step lineage set-up ───────────────────────────


@pytest.mark.asyncio
async def test_manual_edit_creates_new_version_with_parent_pointing_at_edited_version():
    pid = uuid.uuid4()
    current_outline = _sv("outline", 2)
    session = _FakeSession(
        _FakeResult(rows=[current_outline]),  # current() lookup
        _FakeResult(one=2),  # _max_version() lookup inside create()
    )
    svc = VersioningService(session)

    edited = await svc.manual_edit(
        project_id=pid, step="outline", content={"outline": {"hook": "sửa tay"}}, actor="user:abc"
    )

    assert edited.version == 3
    assert edited.parent_version == 2  # points at the version that was edited
    assert edited.created_by == "user:abc"


@pytest.mark.asyncio
async def test_manual_edit_raises_404_when_no_current_version():
    session = _FakeSession(_FakeResult(rows=[]))
    svc = VersioningService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.manual_edit(
            project_id=uuid.uuid4(), step="outline", content={}, actor="user:x"
        )
    assert exc.value.status_code == 404


# ── StepApprovalService.approve() -- 2 sub-step approvals ───────────────────


@pytest.mark.asyncio
async def test_approve_creates_new_approval_row_when_none_exists():
    pid = uuid.uuid4()
    current_outline = _sv("outline", 1)
    session = _FakeSession(
        _FakeResult(rows=[current_outline]),  # VersioningService.current()
        _FakeResult(one=None),  # existing StepApproval lookup -- none yet
    )
    svc = StepApprovalService(session)

    approval = await svc.approve(project_id=pid, step="outline", actor="user:abc")

    assert approval.version == 1
    assert approval.approved is True
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_approve_rejects_non_approvable_step():
    session = _FakeSession()
    svc = StepApprovalService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.approve(project_id=uuid.uuid4(), step="storyboard", actor="user:x")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_approve_404_when_no_version_exists():
    session = _FakeSession(_FakeResult(rows=[]))
    svc = StepApprovalService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.approve(project_id=uuid.uuid4(), step="script", actor="user:x")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_approve_409_when_current_version_all_stale():
    stale_version = _sv("outline", 1, stale=True)
    session = _FakeSession(_FakeResult(rows=[stale_version]))
    svc = StepApprovalService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.approve(project_id=uuid.uuid4(), step="outline", actor="user:x")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_is_current_approved_true_only_when_version_matches():
    pid = uuid.uuid4()
    current_v2 = _sv("outline", 2)
    stale_approval = MagicMock(version=1, approved=True)
    session = _FakeSession(
        _FakeResult(rows=[current_v2]),  # current()
        _FakeResult(one=stale_approval),  # approval row, pinned to old v1
    )
    svc = StepApprovalService(session)
    assert await svc.is_current_approved(pid, "outline") is False
