"""Unit tests for SceneService.reorder_scenes/add_scene/delete_scene/duplicate_scene
(Task 5-4, AC 1-3).

Same fake-AsyncSession pattern as test_scenes_approve.py — no live Postgres,
per rules/testing.md.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.step_version import StepVersion
from app.services.scene_service import SceneNotFoundError, SceneService

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


def _scenes(n: int):
    return [_scene(scene_id=f"s{i + 1}", scene_number=i + 1) for i in range(n)]


def _step_version(version=1, scenes=None):
    sv = MagicMock(spec=StepVersion)
    sv.project_id = PROJECT_ID
    sv.step = "scene_set"
    sv.version = version
    sv.stale = False
    sv.content = {"scenes": scenes if scenes is not None else _scenes(3)}
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
    def __init__(self, step_versions=None, approvals=None):
        self.step_versions = step_versions or []
        self.approvals = approvals or []
        self.flush = AsyncMock()
        self.add = MagicMock(side_effect=self._on_add)

    def _on_add(self, obj):
        if isinstance(obj, StepVersion):
            self.step_versions.append(obj)
        else:
            self.approvals.append(obj)

    async def execute(self, stmt, *a, **kw):
        if "step_versions" in str(stmt):
            rows = sorted(self.step_versions, key=lambda r: r.version, reverse=True)
            return _ExecResult(rows)
        return _ExecResult(list(self.approvals))


@pytest.mark.asyncio
async def test_reorder_moves_scene_and_preserves_ids_ac1():
    """AC-1 (happy): move #4 to position 2 — ids preserved, only scene_number changes."""

    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(5))])
    svc = SceneService(db=session)

    reordered = await svc.reorder_scenes(
        PROJECT_ID, ["s1", "s4", "s2", "s3", "s5"], created_by="creator"
    )

    assert [s["scene_id"] for s in reordered] == ["s1", "s4", "s2", "s3", "s5"]
    assert [s["scene_number"] for s in reordered] == [1, 2, 3, 4, 5]
    # a new scene_set version was inserted (insert-only, BR-3)
    assert len(session.step_versions) == 2


@pytest.mark.asyncio
async def test_reorder_rejects_mismatched_scene_ids():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(3))])
    svc = SceneService(db=session)

    with pytest.raises(SceneNotFoundError):
        await svc.reorder_scenes(PROJECT_ID, ["s1", "s2"], created_by="creator")


@pytest.mark.asyncio
async def test_add_scene_inserts_after_given_position_with_new_id():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(2))])
    svc = SceneService(db=session)

    created = await svc.add_scene(PROJECT_ID, 1, "TextFocus", created_by="creator")

    version = session.step_versions[-1]
    scenes = version.content["scenes"]
    assert [s["scene_id"] for s in scenes] == ["s1", created["scene_id"], "s2"]
    assert created["layout"] == "TextFocus"
    assert created["scene_id"] not in ("s1", "s2")


@pytest.mark.asyncio
async def test_add_scene_to_empty_project_creates_first_version():
    """No scene_set exists yet — add_scene must still work (empty-state → add)."""

    session = _FakeSession(step_versions=[])
    svc = SceneService(db=session)

    created = await svc.add_scene(PROJECT_ID, 0, "Hero", created_by="creator")

    assert len(session.step_versions) == 1
    assert session.step_versions[0].version == 1
    assert created["scene_number"] == 1


@pytest.mark.asyncio
async def test_delete_scene_removes_and_renumbers_ac2():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(3))])
    svc = SceneService(db=session)

    result = await svc.delete_scene(PROJECT_ID, "s2", created_by="creator")

    assert [s["scene_id"] for s in result["scenes"]] == ["s1", "s3"]
    assert [s["scene_number"] for s in result["scenes"]] == [1, 2]
    assert result["deleted_scene_id"] == "s2"


@pytest.mark.asyncio
async def test_delete_last_scene_yields_empty_scene_list_ac2():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(1))])
    svc = SceneService(db=session)

    result = await svc.delete_scene(PROJECT_ID, "s1", created_by="creator")

    assert result["scenes"] == []


@pytest.mark.asyncio
async def test_delete_unknown_scene_raises_not_found():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(2))])
    svc = SceneService(db=session)

    with pytest.raises(SceneNotFoundError):
        await svc.delete_scene(PROJECT_ID, "does-not-exist", created_by="creator")


@pytest.mark.asyncio
async def test_duplicate_scene_mints_new_id_ac3_br4():
    """AC-3/BR-4: copy gets a new scene_id; content matches the original."""

    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(2))])
    svc = SceneService(db=session)

    copy = await svc.duplicate_scene(PROJECT_ID, "s1", created_by="creator")

    version = session.step_versions[-1]
    scenes = version.content["scenes"]
    assert [s["scene_id"] for s in scenes] == ["s1", copy["scene_id"], "s2"]
    assert copy["scene_id"] != "s1"
    assert copy["layout"] == "Hero"
    assert copy["texts"] == scenes[0]["texts"]


@pytest.mark.asyncio
async def test_duplicate_then_edit_copy_does_not_mutate_original_ac3_br4():
    """AC-3/BR-4: editing the duplicate (a further update_scene call) never
    touches the original row — they are independent dict copies server-side."""

    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(1))])
    svc = SceneService(db=session)

    copy = await svc.duplicate_scene(PROJECT_ID, "s1", created_by="creator")
    updated_copy = await svc.update_scene(
        PROJECT_ID, copy["scene_id"], {"duration_ms": 9000}, created_by="creator"
    )

    latest_version = session.step_versions[-1]
    original = next(s for s in latest_version.content["scenes"] if s["scene_id"] == "s1")

    assert updated_copy["duration_ms"] == 9000
    assert original["duration_ms"] == 6000


@pytest.mark.asyncio
async def test_duplicate_unknown_scene_raises_not_found():
    session = _FakeSession(step_versions=[_step_version(scenes=_scenes(1))])
    svc = SceneService(db=session)

    with pytest.raises(SceneNotFoundError):
        await svc.duplicate_scene(PROJECT_ID, "does-not-exist", created_by="creator")
