"""PipelineRun model -- Task 4-1: one row per LangGraph pipeline execution.

This is the row RunService reads/writes to enforce BR-1 (one active run per
project), BR-2 (approve only valid at the exact interrupted node), and BR-4
(retry exhaustion -> FAILED, previous_status kept for a future resume
feature, 1-4 BR-3). The LangGraph checkpoint itself (graph position, full
PipelineState) lives in the ``langgraph`` library's own tables
(app/pipeline/checkpoint.py) keyed by ``thread_id = str(PipelineRun.id)`` --
this row is the lightweight, query-friendly index into that checkpoint,
not a duplicate of it.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass

# Runs in one of these statuses count as "active" for BR-1 (409 on new POST run).
ACTIVE_RUN_STATUSES: frozenset[str] = frozenset({"pending", "running", "interrupted"})


class PipelineRun(Base):
    """One row per pipeline run (correlation_id = str(id))."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    current_node: Mapped[str | None] = mapped_column(String(20), nullable=True)
    interrupted_node: Mapped[str | None] = mapped_column(String(20), nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Task 4-7 Step 2 (migration 012): set by RunService.cancel_run(), checked
    # by _execute_node right after the in-flight node's ainvoke() returns --
    # not a "cancelling" status value, so it survives a crash mid-cancel
    # without any ambiguity about which write happened first (BR-1).
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
