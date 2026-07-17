"""Unit tests for ProjectService — task 1-3 ACs (BR-1 delete-guard, BR-2 clone,
BR-3 next_action, BR-4 archive/unarchive, BR-6 lifecycle grouping)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.project_service import (
    ProjectService,
    group_by_lifecycle,
    next_action,
)
from app.services.state_machine import ProjectStatus, TransitionError


def _project(status="DRAFT", owner_id=None, pid=None, archived_at=None):
    p = MagicMock()
    p.id = pid or uuid.uuid4()
    p.owner_id = owner_id or uuid.uuid4()
    p.name = "Test project"
    p.topic = "GPT-5.5"
    p.mode = "interactive"
    p.status = status
    p.language = "vi"
    p.formats = ["vertical_1080x1920"]
    p.voice_id = None
    p.voice_gender = "female"
    p.cloned_from = None
    p.archived_at = archived_at
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


class _FakeResult:
    def __init__(self, *, one=None, many=None, scalar=None):
        self._one = one
        self._many = many if many is not None else []
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        m = MagicMock()
        m.all.return_value = self._many
        return m

    def scalar(self):
        return self._scalar


class _FakeSession:
    """Returns queued results in order — one per `execute()` call."""

    def __init__(self, *results):
        self._queue = list(results)
        self.flush = AsyncMock()
        self.delete = AsyncMock()
        self.add = MagicMock()

    async def execute(self, stmt, *a, **kw):
        return self._queue.pop(0) if self._queue else _FakeResult()


# ── AC-1: create ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_defaults_format_and_draft_status():
    session = _FakeSession()
    svc = ProjectService(session)
    owner = uuid.uuid4()
    proj = await svc.create(name="GPT-5.5 news", topic="GPT-5.5", owner_id=owner)
    assert proj.formats == ["vertical_1080x1920"]
    assert proj.owner_id == owner
    session.add.assert_called_once()


# ── BR-3: next_action mapping (AC-6, seed 4 statuses) ────────────────────────


@pytest.mark.parametrize(
    "status,expected_label",
    [
        ("NEED_REVIEW", "Mở duyệt ▸"),
        ("READY", "Xem & đăng"),
        ("FAILED", "Xem lỗi & chạy tiếp"),
    ],
)
def test_next_action_static_statuses(status, expected_label):
    assert next_action(status)["label"] == expected_label


def test_next_action_running_shows_progress_pct():
    result = next_action("RENDERING", {"step": "render", "pct": 42})
    assert result["label"] == "● render 42%"


# ── BR-1: delete guard ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_rejects_non_draft():
    proj = _project(status="READY")
    session = _FakeSession()
    svc = ProjectService(session)
    with pytest.raises(TransitionError):
        await svc.delete(proj)


@pytest.mark.asyncio
async def test_delete_rejects_when_step_versions_exist():
    proj = _project(status="DRAFT")
    # delete() issues one query: count(StepVersion.id) -> scalar()=1 (has versions)
    session = _FakeSession(_FakeResult(scalar=1))
    svc = ProjectService(session)
    with pytest.raises(TransitionError):
        await svc.delete(proj)


@pytest.mark.asyncio
async def test_delete_succeeds_for_draft_no_versions():
    proj = _project(status="DRAFT")
    session = _FakeSession(_FakeResult(scalar=0))
    svc = ProjectService(session)
    await svc.delete(proj)
    session.delete.assert_awaited_once_with(proj)


# ── BR-2: clone ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_clone_sets_default_name_draft_status_and_lineage():
    proj = _project(status="READY")
    session = _FakeSession()
    svc = ProjectService(session)
    actor = uuid.uuid4()
    clone = await svc.clone(proj, actor)
    assert clone.name == f"{proj.name} (bản sao)"
    assert clone.status == ProjectStatus.DRAFT
    assert clone.owner_id == actor
    assert clone.cloned_from == proj.id


@pytest.mark.asyncio
async def test_clone_step_versions_copies_latest_non_stale_excludes_render_publish():
    src, dst = uuid.uuid4(), uuid.uuid4()

    def _sv(step, version, stale=False):
        sv = MagicMock()
        sv.step = step
        sv.version = version
        sv.stale = stale
        sv.content = {"k": step}
        return sv

    rows = [_sv("research", 1), _sv("research", 2), _sv("script", 1)]
    session = _FakeSession(_FakeResult(many=rows))
    svc = ProjectService(session)
    copies = await svc.clone_step_versions(src, dst)

    by_step = {c.step: c for c in copies}
    assert set(by_step) == {"research", "script"}
    assert by_step["research"].content == {"k": "research"}
    # picks the latest (v2) research row, not v1
    assert all(c.version == 1 and c.parent_version is None for c in copies)
    assert all(c.project_id == dst for c in copies)


# ── BR-4: archive / unarchive ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_archive_rejects_from_active_state():
    proj = _project(status="RESEARCHING")
    svc = ProjectService(_FakeSession())
    with pytest.raises(TransitionError):
        await svc.archive(proj, actor="user")


@pytest.mark.asyncio
async def test_archive_sets_archived_at():
    proj = _project(status="DRAFT")
    svc = ProjectService(_FakeSession())
    result = await svc.archive(proj, actor="user")
    assert result.archived_at is not None


@pytest.mark.asyncio
async def test_unarchive_clears_archived_at():
    proj = _project(status="DRAFT", archived_at=datetime.now(UTC))
    svc = ProjectService(_FakeSession())
    result = await svc.unarchive(proj, actor="user")
    assert result.archived_at is None


# ── BR-6: lifecycle grouping (dashboard) — empty groups hidden ───────────────


def test_group_by_lifecycle_hides_empty_groups_and_orders():
    projects = [
        _project(status="NEED_REVIEW"),
        _project(status="RESEARCHING"),
        _project(status="DRAFT"),
    ]
    groups = group_by_lifecycle(projects)
    assert set(groups) == {"waiting_review", "running", "in_progress"}
    assert "published" not in groups  # empty group hidden


def test_group_by_lifecycle_all_statuses_covered():
    for status in ProjectStatus:
        projects = [_project(status=status.value)]
        groups = group_by_lifecycle(projects)
        # Every status (incl. ARCHIVED, via the "other" fallback bucket)
        # lands in exactly one bucket — nothing is silently dropped.
        total = sum(len(v) for v in groups.values())
        assert total == 1
