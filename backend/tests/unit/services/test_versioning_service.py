"""Unit tests for VersioningService — task 1-5 ACs.

AC-1 restore cascade-stale, AC-2 regenerate parent-tracking, AC-3 all_stale
flag, AC-4 scene_set compare, AC-5 404/409 error paths.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.versioning_service import VersioningService


def _sv(step, version, *, stale=False, content=None, parent_version=None, created_by="user"):
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.step = step
    sv.version = version
    sv.stale = stale
    sv.content = content or {}
    sv.parent_version = parent_version
    sv.created_by = created_by
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
    """Returns queued results in order — one per `execute()` call."""

    def __init__(self, *results):
        self._queue = list(results)
        self.flush = AsyncMock()
        self.add = MagicMock()

    async def execute(self, stmt, *a, **kw):
        return self._queue.pop(0) if self._queue else _FakeResult()


# ── create() — insert-only, auto-increment (BR-1) ───────────────────────────


@pytest.mark.asyncio
async def test_create_auto_increments_version():
    pid = uuid.uuid4()
    # _max_version query returns scalar_one_or_none() = 2
    session = _FakeSession(_FakeResult(one=2))
    svc = VersioningService(session)
    sv = await svc.create(project_id=pid, step="research", content={"a": 1}, actor="ai")
    assert sv.version == 3
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_first_version_is_1():
    session = _FakeSession(_FakeResult(one=None))
    svc = VersioningService(session)
    sv = await svc.create(project_id=uuid.uuid4(), step="research", content={}, actor="ai")
    assert sv.version == 1


# ── current() — BR-4 max non-stale, all_stale flag (AC-3) ───────────────────


@pytest.mark.asyncio
async def test_current_returns_max_non_stale():
    versions = [_sv("script", 2, stale=True), _sv("script", 1, stale=False)]
    session = _FakeSession(_FakeResult(rows=versions))
    svc = VersioningService(session)
    current, all_stale = await svc.current(uuid.uuid4(), "script")
    assert current.version == 1
    assert all_stale is False


@pytest.mark.asyncio
async def test_current_all_stale_returns_max_with_flag():
    versions = [_sv("script", 2, stale=True), _sv("script", 1, stale=True)]
    session = _FakeSession(_FakeResult(rows=versions))
    svc = VersioningService(session)
    current, all_stale = await svc.current(uuid.uuid4(), "script")
    assert current.version == 2
    assert all_stale is True


@pytest.mark.asyncio
async def test_current_no_versions_returns_none():
    session = _FakeSession(_FakeResult(rows=[]))
    svc = VersioningService(session)
    current, all_stale = await svc.current(uuid.uuid4(), "script")
    assert current is None
    assert all_stale is False


# ── restore() — cascade-stale downstream only (AC-1, BR-3) ──────────────────


@pytest.mark.asyncio
async def test_restore_marks_downstream_stale_not_self():
    target = _sv("research", 1)
    downstream_versions = [_sv("outline", 3), _sv("script", 2)]
    session = _FakeSession(
        _FakeResult(one=target),  # target lookup
        _FakeResult(rows=downstream_versions),  # downstream non-stale versions
    )
    svc = VersioningService(session)
    restored, staled = await svc.restore(
        project_id=uuid.uuid4(), step="research", version=1, actor="user"
    )
    assert restored is target
    assert set(staled) == {"outline", "script"}
    assert all(v.stale for v in downstream_versions)
    assert target.stale is False  # restored step itself never staled


@pytest.mark.asyncio
async def test_restore_missing_version_raises_404():
    session = _FakeSession(_FakeResult(one=None))
    svc = VersioningService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.restore(project_id=uuid.uuid4(), step="research", version=99, actor="user")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_restore_last_step_has_no_downstream_to_stale():
    target = _sv("publish", 1)
    session = _FakeSession(_FakeResult(one=target))
    svc = VersioningService(session)
    _, staled = await svc.restore(project_id=uuid.uuid4(), step="publish", version=1, actor="user")
    assert staled == []


# ── compare() — text diff + scene_set diff (AC-2, AC-4, BR-6) ───────────────


@pytest.mark.asyncio
async def test_compare_text_diff_for_script_step():
    v1 = _sv("script", 2, content={"script_text": "hello world"})
    v2 = _sv("script", 3, content={"script_text": "hello brave world"})
    session = _FakeSession(_FakeResult(one=v1), _FakeResult(one=v2))
    svc = VersioningService(session)
    result = await svc.compare(uuid.uuid4(), "script", 2, 3)
    assert result["type"] == "text"
    assert "brave" in result["diff"]


@pytest.mark.asyncio
async def test_compare_scene_set_added_removed_changed():
    v1 = _sv(
        "scene_set",
        1,
        content={"scenes": [{"scene_id": "s1", "text": "a"}, {"scene_id": "s2", "text": "b"}]},
    )
    v2 = _sv(
        "scene_set",
        2,
        content={"scenes": [{"scene_id": "s1", "text": "a-changed"}, {"scene_id": "s3", "text": "c"}]},
    )
    session = _FakeSession(_FakeResult(one=v1), _FakeResult(one=v2))
    svc = VersioningService(session)
    result = await svc.compare(uuid.uuid4(), "scene_set", 1, 2)
    assert result["type"] == "scene_set"
    assert result["added"] == ["s3"]
    assert result["removed"] == ["s2"]
    assert result["changed"] == [{"scene_id": "s1", "fields": ["text"]}]


@pytest.mark.asyncio
async def test_compare_missing_version_raises_404():
    session = _FakeSession(_FakeResult(one=None))
    svc = VersioningService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.compare(uuid.uuid4(), "script", 1, 2)
    assert exc.value.status_code == 404


# ── get() — task 5-9 additive 'Xem' content accessor ─────────────────────────


@pytest.mark.asyncio
async def test_get_returns_full_row_including_content():
    """5-9: the only way to view a past version's raw content — list/current/
    restore's VersionOut never carries it, and compare() only ever returns a
    diff/scene-diff for the four content-bearing steps."""
    pid = uuid.uuid4()
    sv = _sv("scene_set", 2, content={"scenes": [{"scene_id": "s1"}]})
    session = _FakeSession(_FakeResult(one=sv))
    svc = VersioningService(session)

    result = await svc.get(pid, "scene_set", 2)

    assert result is sv
    assert result.content == {"scenes": [{"scene_id": "s1"}]}


@pytest.mark.asyncio
async def test_get_missing_version_raises_404():
    session = _FakeSession(_FakeResult(one=None))
    svc = VersioningService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.get(uuid.uuid4(), "scene_set", 99)
    assert exc.value.status_code == 404
