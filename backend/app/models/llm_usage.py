"""Usage tracking for provider calls (Task 3-5 FR-18).

Partitioned by month on created_at per rules/performance.md
("high-volume tables partitioned by month from the first migration").
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.api_key import ApiKey


class LlmUsage(Base):
    """One LLM (or embedding) call record.

    Partitioned by RANGE on created_at (daily_cost_cap checks this table).
    partition key must be the first column in the primary key definition
    so PostgreSQL can route inserts without consulting the index.
    """

    __tablename__ = "llm_usage"

    # ── partition key ──────────────────────────────────────────────────

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        # partition key — must be in PK so routing works
        nullable=False,
        server_default="now()",
    )

    # ── content ────────────────────────────────────────────────────────

    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    api_key_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    task: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
        comment="pipeline node / agent name",
    )
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="cheap | strong | embedding",
    )
    project_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cost_estimate: Mapped[float] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        server_default="0",
        comment="USD estimate from published price list (not invoice)",
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        CheckConstraint(
            "tier IN ('cheap', 'strong', 'embedding')",
            name="ck_llm_usage_tier",
        ),
        CheckConstraint(
            "tokens_in >= 0 AND tokens_out >= 0",
            name="ck_llm_usage_tokens_nonneg",
        ),
        CheckConstraint(
            "cost_estimate >= 0",
            name="ck_llm_usage_cost_nonneg",
        ),
    )
