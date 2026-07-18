"""Project summary response schema — task 5-10 FR-01.

Aggregated view for ProjectDrawer: metadata + AI summary + verdict +
estimated cost + source count + recent activity.
"""

from __future__ import annotations

from datetime import datetime, UTC
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectSummaryMeta(BaseModel):
    """Core project metadata for the drawer."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    topic: str
    mode: str
    status: str
    language: str
    formats: list[str]
    voice_id: str | None = None
    voice_gender: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SourceCountOut(BaseModel):
    """Source statistics for the summary."""

    total: int = 0
    trusted: int = 0
    pinned: int = 0
    disabled: int = 0


class ActivityEntry(BaseModel):
    """One status-history entry (most recent 5)."""

    from_status: str
    to_status: str
    actor: str
    reason: str | None
    created_at: datetime


class ProjectSummaryOut(BaseModel):
    """Single response body for GET /projects/{id}/summary.

    All cost fields carry the "ước tính" (estimate) qualifier per BR-4.
    """

    model_config = ConfigDict(from_attributes=True)

    project: ProjectSummaryMeta
    # AI-generated (cached, post-research only); null = not yet generated
    ai_summary: str | None = None

    # Fact-check verdict from most recent research/claims
    overall_verdict: str | None = None

    # Pipeline metadata
    scene_count: int = 0
    duration_estimate_ms: int | None = None

    # Cost: sum of llm_usage for this project, tagged "ước tính"
    estimated_cost_usd: float = 0.0
    estimated_cost_label: str = "ước tính"

    # Source stats
    source_count: SourceCountOut

    # Last 5 status transitions
    recent_activity: list[ActivityEntry] = []
