"""AC4 (Task 5-3) regression: a raw, non-allowlisted asset URL through
``PUT /projects/{id}/scenes/{scene_id}`` must be rejected (422), never
silently accepted — SSRF defense-in-depth per rules/security.md. Kept as a
standing test, not a one-off, per the task's DoD ("test bảo mật URL trần
giữ vĩnh viễn").

Exercises ``SceneService.update_scene`` directly with a fake AsyncSession
(same pattern as test_scenes_approve.py) — no DB/network per rules/testing.md.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.step_version import StepVersion
from app.services.scene_service import SceneService
from app.services.scene_validator import SceneValidationError

PROJECT_ID = "11111111-1111-1111-1111-111111111111"


def _scene_with_image(url: str | None = None, asset_id: str | None = None):
    asset: dict[str, object] = {}
    if asset_id is not None:
        asset["asset_id"] = asset_id
    if url is not None:
        asset["url"] = url
    return {
        "scene_id": "s1",
        "schema_version": "1.0.0",
        "scene_number": 1,
        "duration_ms": 6000,
        "layout": "MediaFull",
        "background": {"type": "color", "color": "#000000"},
        "texts": [],
        "images": [
            {
                "id": "img1",
                "asset": asset,
                "fit": "cover",
                "ken_burns": True,
            }
        ],
        "subtitle": {"enabled": True, "style": "line"},
        "transition": {"type": "none", "duration_ms": 300},
    }


def _step_version(scenes):
    sv = MagicMock(spec=StepVersion)
    sv.project_id = PROJECT_ID
    sv.step = "scene_set"
    sv.version = 1
    sv.stale = False
    sv.content = {"scenes": scenes}
    return sv


class _ExecResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        class _Scalars:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

        return _Scalars(self._rows)


class _FakeSession:
    def __init__(self, step_versions):
        self.step_versions = step_versions
        self.flush = AsyncMock()
        self.add = MagicMock()

    async def execute(self, stmt, *a, **kw):
        if "step_versions" in str(stmt):
            return _ExecResult(sorted(self.step_versions, key=lambda r: r.version, reverse=True))
        return _ExecResult([])


@pytest.mark.asyncio
async def test_raw_non_allowlisted_url_rejected_with_422_field_path():
    session = _FakeSession([_step_version([_scene_with_image()])])
    svc = SceneService(db=session)

    with pytest.raises(SceneValidationError) as exc_info:
        await svc.update_scene(
            PROJECT_ID,
            "s1",
            {"images": [{"id": "img1", "asset": {"url": "https://evil.example.com/x.jpg"}}]},
            created_by="creator",
        )

    assert "asset.url" in exc_info.value.field_path


@pytest.mark.asyncio
async def test_allowlisted_pexels_cdn_url_is_accepted():
    session = _FakeSession([_step_version([_scene_with_image()])])
    svc = SceneService(db=session)

    result = await svc.update_scene(
        PROJECT_ID,
        "s1",
        {
            "images": [
                {
                    "id": "img1",
                    "asset": {"url": "https://images.pexels.com/photos/1/gpu.jpg"},
                }
            ]
        },
        created_by="creator",
    )

    assert result["images"][0]["asset"]["url"] == "https://images.pexels.com/photos/1/gpu.jpg"


@pytest.mark.asyncio
async def test_asset_id_reference_bypasses_url_check_entirely():
    """The common/expected path: no raw url at all, just an internal asset_id."""
    session = _FakeSession([_step_version([_scene_with_image(asset_id="a1")])])
    svc = SceneService(db=session)

    result = await svc.update_scene(
        PROJECT_ID,
        "s1",
        {"images": [{"id": "img1", "asset": {"asset_id": "a2"}}]},
        created_by="creator",
    )

    assert result["images"][0]["asset"]["asset_id"] == "a2"
