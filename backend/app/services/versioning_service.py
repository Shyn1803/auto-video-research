"""Versioning service (task 1-5).

Inserts-only per BR-1 - never UPDATEs content, always INSERTs a new version.
Cascade-stale only marks downstream steps (BR-3).
"""
from __future__ import annotations

import difflib
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step_version import StepVersion, _STEP_ORDER

logger = logging.getLogger(__name__)


class VersioningService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        project_id: UUID,
        step: str,
        content: dict,
        actor: str = "system",
        parent_version: int | None = None,
    ) -> StepVersion:
        max_v = await self._max_version(project_id, step)
        sv = StepVersion(
            project_id=project_id,
            step=step,
            version=max_v + 1,
            content=content,
            parent_version=parent_version or max_v,
            stale=False,
            created_by=actor,
        )
        self._db.add(sv)
        await self._db.flush()
        return sv

    async def current(self, project_id: UUID, step: str) -> tuple[StepVersion | None, bool]:
        result = await self._db.execute(
            select(StepVersion)
            .where(StepVersion.project_id == project_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
        )
        versions = list(result.scalars().all())
        if not versions:
            return None, False
        non_stale = [v for v in versions if not v.stale]
        if non_stale:
            return max(non_stale, key=lambda v: v.version), False
        return max(versions, key=lambda v: v.version), True

    async def restore(
        self,
        *,
        project_id: UUID,
        step: str,
        version: int,
        actor: str,
    ) -> tuple[StepVersion, list[str]]:
        result = await self._db.execute(
            select(StepVersion).where(
                StepVersion.project_id == project_id,
                StepVersion.step == step,
                StepVersion.version == version,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")

        step_idx = _STEP_ORDER.index(step)
        downstream = list(_STEP_ORDER[step_idx + 1 :])

        staled: list[str] = []
        if downstream:
            res = await self._db.execute(
                select(StepVersion).where(
                    StepVersion.project_id == project_id,
                    StepVersion.step.in_(downstream),
                    StepVersion.stale.is_(False),
                )
            )
            for sv in res.scalars().all():
                sv.stale = True
                if sv.step not in staled:
                    staled.append(sv.step)
            await self._db.flush()

        logger.info("restored project=%s step=%s v=%d actor=%s staled=%s", project_id, step, version, actor, staled)
        return target, staled

    async def compare(
        self,
        project_id: UUID,
        step: str,
        v1: int,
        v2: int,
    ) -> dict:
        a = await self._get_version(project_id, step, v1)
        b = await self._get_version(project_id, step, v2)
        ca, cb = a.content, b.content

        if step in ("outline", "script"):
            ta, tb = _text_content(ca), _text_content(cb)
            diff = list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), lineterm="", n=3))
            return {"type": "text", "diff": chr(10).join(diff)}
        if step in ("storyboard", "scene_set"):
            scenes_a = ca.get("scenes", [])
            scenes_b = cb.get("scenes", [])
            map_a = {s.get("scene_id"): s for s in scenes_a}
            map_b = {s.get("scene_id"): s for s in scenes_b}
            added = [sid for sid in map_b if sid not in map_a]
            removed = [sid for sid in map_a if sid not in map_b]
            changed = [
                {"scene_id": sid, "fields": [k for k in map_a[sid] if map_a[sid].get(k) != map_b[sid].get(k)]}
                for sid in map_a
                if sid in map_b and map_a[sid] != map_b[sid]
            ]
            return {"type": "scene_set", "added": added, "removed": removed, "changed": changed}
        return {"type": "raw", "v1_content": ca, "v2_content": cb}

    async def get(self, project_id: UUID, step: str, version: int) -> StepVersion:
        """Public accessor for a single version's full row (incl. content) —
        task 5-9's 'Xem' readonly-view needs this; compare()/current()/list()
        never expose raw content for the four content-bearing steps."""
        return await self._get_version(project_id, step, version)

    async def _max_version(self, project_id: UUID, step: str) -> int:
        result = await self._db.execute(
            select(StepVersion.version)
            .where(StepVersion.project_id == project_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row or 0

    async def _get_version(self, project_id: UUID, step: str, version: int) -> StepVersion:
        result = await self._db.execute(
            select(StepVersion).where(
                StepVersion.project_id == project_id,
                StepVersion.step == step,
                StepVersion.version == version,
            )
        )
        sv = result.scalar_one_or_none()
        if sv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
        return sv


def _text_content(content: dict) -> str:
    for key in ("text", "outline_text", "script_text", "body"):
        if key in content:
            return str(content[key])
    return str(content)
