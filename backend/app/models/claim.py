"""Claim model -- Task 4-4 FR-04 (docs/specs/database-schema.md §2.4).

``evidence`` is a JSONB array of ``{source_id, quote, supports}`` -- BR-3
requires override to never delete evidence, only change ``verdict`` (+
record who/when/why via the ``overridden_*`` columns, which double as the
lightweight audit trail AC4 needs to be "queryable").
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project

CLAIM_TYPES = (
    "model_name", "benchmark", "release_date", "paper", "github", "version", "other",
)
VERDICTS = ("PASS", "WARN", "FAIL", "PENDING")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    project_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(20), nullable=False)
    verdict: Mapped[str] = mapped_column(String(10), nullable=False, server_default="PENDING")
    evidence: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # BR-3 audit trail: who/when/why overrode this claim's verdict (never
    # clears evidence -- only this bookkeeping + verdict itself change).
    overridden_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship("Project")

    __table_args__ = (
        CheckConstraint(
            "claim_type IN ('model_name','benchmark','release_date','paper','github','version','other')",
            name="ck_claims_claim_type",
        ),
        CheckConstraint(
            "verdict IN ('PASS','WARN','FAIL','PENDING')", name="ck_claims_verdict"
        ),
    )
