"""Unit tests for SceneService.approve_scene / update_scene (Task 5-1 AC-1, AC-3).

Uses a fake AsyncSession (same pattern as test_user_admin_service.py) rather
than a real Postgres connection — this suite must pass with zero DB/network
access per rules/testing.md.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.scene_approval import SceneApproval
from app.models.step_version import StepVersion
from app.services.scene_service import SceneNotFoundError, SceneService
from app.services.scene_validator import SceneValidationError

PROJECT_ID = "11111111-1111-1111-1111-111111111111"


def _scene(scene_id="s1", scene_number=1, duration_ms=6000, layout="Hero"):
    return {
        "scene_id": scene_id,
        "schema_version": "1.0.0",
        "scene_number": scene_number,
        "duration_ms": duration_ms,
        "layout": layout,
        "background": {"type": "color", "color": "#000000"},
        "texts": [
            {
                "id": "t1",
                "content": "Xin chào",
                "role": "heading",
                "position": "center",
            }
        ],
        "images": [],
        "subtitle": {"enabled": True, "style": "line"},
        "transition": {"type": "none", "duration_ms": 300},
    }


def _step_version(version=1, scenes=None):
    sv = MagicMock(spec=StepVersion)
    sv.project_id = PROJECT_ID
    sv.step = "scene_set"
    sv.version = version
    sv.stale = False
    sv.content = {"scenes": scenes if scenes is not None else [_scene()]}
    return sv


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _ScalarsResult(self._rows)


class _FakeSession:
    """Returns step_version rows for the first query, approval rows for the second."""

    def __init__(self, step_versions=None, approvals=None):
        self.step_versions = step_versions or []
        self.approvals = approvals or []
        self.flush = AsyncMock()
        self.add = MagicMock(side_effect=self._on_add)

    def _on_add(self, obj):
        if isinstance(obj, SceneApproval):
            self.approvals = [a for a in self.approvals if a.scene_id != obj.scene_id]
            self.approvals.append(obj)
        elif isinstance(obj, StepVersion):
            self.step_versions.append(obj)

    async def execute(self, stmt, *a, **kw):
        # Distinguish by the table the query targets (StepVersion vs SceneApproval).
        if "step_versions" in str(stmt):
            rows = sorted(self.step_versions, key=lambda r: r.version, reverse=True)
            return _ExecResult(rows)
        return _ExecResult(list(self.approvals))


@pytest.mark.asyncio
async def test_approve_scene_creates_approval_row():
    session = _FakeSession(step_versions=[_step_version()])
    svc = SceneService(db=session)

    result = await svc.approve_scene(PROJECT_ID, "s1", user_id="u1")

    assert result["approved"] is True
    assert len(session.approvals) == 1
    assert session.approvals[0].approved is True
    assert session.approvals[0].scene_id == "s1"


@pytest.mark.asyncio
async def test_approve_unknown_scene_raises_not_found():
    session = _FakeSession(step_versions=[_step_version()])
    svc = SceneService(db=session)

    with pytest.raises(SceneNotFoundError):
        await svc.approve_scene(PROJECT_ID, "does-not-exist", user_id="u1")


@pytest.mark.asyncio
async def test_list_scenes_reports_approved_flag():
    approval = MagicMock(spec=SceneApproval)
    approval.scene_id = "s1"
    approval.approved = True
    session = _FakeSession(step_versions=[_step_version()], approvals=[approval])
    svc = SceneService(db=session)

    scenes = await svc.list_scenes(PROJECT_ID)

    assert scenes[0]["approved"] is True


@pytest.mark.asyncio
async def test_update_scene_clears_prior_approval():
    approval = MagicMock(spec=SceneApproval)
    approval.scene_id = "s1"
    approval.approved = True
    session = _FakeSession(step_versions=[_step_version()], approvals=[approval])
    svc = SceneService(db=session)

    updated = await svc.update_scene(
        PROJECT_ID, "s1", {"duration_ms": 8000}, created_by="creator"
    )

    assert updated["approved"] is False
    assert approval.approved is False
    # a new scene_set version was inserted (insert-only, never UPDATE content)
    assert len(session.step_versions) == 2


@pytest.mark.asyncio
async def test_update_scene_invalid_payload_raises_validation_error():
    session = _FakeSession(step_versions=[_step_version()])
    svc = SceneService(db=session)

    with pytest.raises(SceneValidationError):
        await svc.update_scene(
            PROJECT_ID, "s1", {"duration_ms": 500}, created_by="creator"
        )
