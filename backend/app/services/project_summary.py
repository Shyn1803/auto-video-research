"""Project summary aggregation service — task 5-10 FR-01.

Produces the ProjectSummaryOut payload for the new GET /projects/{id}/summary
endpoint.  Ownership enforcement (🅞) happens here: callers may only retrieve
summaries for projects they own (or as admin).

AI summary is stored in the research step_version content (key: "ai_summary"),
generated once by the research node — this service reads the cached value but
never triggers LLM calls.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim
from app.models.llm_usage import LlmUsage
from app.models.project import Project
from app.models.source import Source
from app.models.status_history import StatusHistory
from app.schemas.project_summary import (
    ActivityEntry,
    ProjectSummaryMeta,
    ProjectSummaryOut,
    SourceCountOut,
)

logger = logging.getLogger("avr.project_summary")


class ProjectSummaryService:
    """Aggregate a project's summary data for ProjectDrawer."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_summary(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectSummaryOut | None:
        """Return the summary for *project_id* owned by *user_id*, or None.

        Caller is responsible for mapping None → 404 and unauthorized → 403.
        """
        proj = await self._get_project(project_id, user_id)
        if proj is None:
            return None

        overall_verdict = await self._compute_verdict(project_id)
        cost_rows = await self._get_cost_rows(project_id)
        source_stats = await self._get_source_stats(project_id)
        recent_activity = await self._get_recent_activity(project_id)
        scene_count = await self._get_scene_count(project_id)
        ai_summary = await self._get_ai_summary(project_id)

        return ProjectSummaryOut(
            project=ProjectSummaryMeta(
                id=proj.id,
                name=proj.name,
                topic=proj.topic,
                mode=proj.mode,
                status=proj.status,
                language=proj.language,
                formats=[
                    f.strip()
                    for f in (
                        proj.formats.strip("{}").split(",")
                        if isinstance(proj.formats, str)
                        else proj.formats
                    )
                    or []
                ],
                voice_id=proj.voice_id,
                voice_gender=proj.voice_gender,
                archived_at=proj.archived_at,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            ),
            ai_summary=ai_summary,
            overall_verdict=overall_verdict,
            scene_count=scene_count,
            # Duration estimate requires scene_set content — approximate to 0 for now
            duration_estimate_ms=None,
            estimated_cost_usd=sum(r.cost_estimate for r in cost_rows),
            source_count=source_stats,
            recent_activity=recent_activity,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    async def _get_project(
        self, project_id: UUID, user_id: UUID
    ) -> Project | None:
        """Fetch project by id+owner (covers archived projects too)."""
        result = await self._db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _compute_verdict(self, project_id: UUID) -> str | None:
        """Derive overall verdict from claims: PASS if all PASS, FAIL if any
        FAIL, else WARN.  Returns None when no claims exist."""
        result = await self._db.execute(
            select(Claim.verdict).where(Claim.project_id == str(project_id))
        )
        verdicts = [row[0] for row in result.all()]
        if not verdicts:
            return None
        if all(v == "PASS" for v in verdicts):
            return "PASS"
        if any(v == "FAIL" for v in verdicts):
            return "FAIL"
        return "WARN"

    async def _get_cost_rows(self, project_id: UUID) -> list[Any]:
        """All successful llm_usage rows for this project."""
        result = await self._db.execute(
            select(LlmUsage)
            .where(
                LlmUsage.project_id == str(project_id),
                LlmUsage.success.is_(True),
            )
            .order_by(LlmUsage.created_at.desc())
        )
        return list(result.scalars().all())

    async def _get_source_stats(self, project_id: UUID) -> SourceCountOut:
        """Count sources by flag (total, trusted, pinned, disabled)."""
        result = await self._db.execute(
            select(
                func.count(Source.id).label("total"),
                func.count(Source.id)
                .filter(Source.trusted.is_(True))
                .label("trusted"),
                func.count(Source.id)
                .filter(Source.pinned.is_(True))
                .label("pinned"),
                func.count(Source.id)
                .filter(Source.disabled.is_(True))
                .label("disabled"),
            ).where(Source.project_id == str(project_id))
        )
        row = result.one_or_none()
        if row is None:
            return SourceCountOut()
        return SourceCountOut(
            total=int(row.total or 0),
            trusted=int(row.trusted or 0),
            pinned=int(row.pinned or 0),
            disabled=int(row.disabled or 0),
        )

    async def _get_recent_activity(
        self, project_id: UUID, limit: int = 5
    ) -> list[ActivityEntry]:
        """Last ``limit`` status-history entries, newest first."""
        result = await self._db.execute(
            select(StatusHistory)
            .where(StatusHistory.project_id == str(project_id))
            .order_by(StatusHistory.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            ActivityEntry(
                from_status=r.from_status,
                to_status=r.to_status,
                actor=r.actor,
                reason=r.reason,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def _get_scene_count(self, project_id: UUID) -> int:
        """Count non-stale step_versions for the scene_set step."""
        from app.models.step_version import StepVersion

        result = await self._db.execute(
            select(func.count(StepVersion.id))
            .where(
                StepVersion.project_id == str(project_id),
                StepVersion.step == "scene_set",
                StepVersion.stale.is_(False),
            )
        )
        return int(result.scalar() or 0)

    async def _get_ai_summary(self, project_id: UUID) -> str | None:
        """Read cached AI summary from the research step_version content.

        Step 2 wires this: after research completes, the research node stores
        the 2-sentence summary under content['ai_summary'].  This method only
        reads — it never triggers an LLM call.
        """
        from app.models.step_version import StepVersion

        result = await self._db.execute(
            select(StepVersion)
            .where(
                StepVersion.project_id == str(project_id),
                StepVersion.step == "research",
                StepVersion.stale.is_(False),
            )
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        sv = result.scalar_one_or_none()
        if sv is None or not sv.content:
            return None
        return sv.content.get("ai_summary")
