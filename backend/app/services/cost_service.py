"""Cost service — /admin/costs (Task 3-5 FR-18 / BR-4).

All cost values returned are estimates (BR-4: "hiển thị = ước tính từ bảng giá").
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

logger = logging.getLogger("avr.cost_service")

VALID_GROUP_BY = frozenset({"task", "provider", "tier", "model", "project_id"})
DEFAULT_DAYS = 30


class CostBucket:
    """One aggregated row from the cost query."""

    group_key: str = ""
    group_label: str = ""
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimate_usd: float = 0.0
    is_estimate: bool = True


class CostService:
    """Query llm_usage with flexible grouping."""

    def __init__(self, session_factory: Any) -> None:
        self._sf = session_factory

    async def query(
        self,
        group_by: str = "task",
        days: int | None = None,
    ) -> list[CostBucket]:
        if group_by not in VALID_GROUP_BY:
            raise ValueError(
                f"invalid group_by={group_by!r}; "
                f"valid: {sorted(VALID_GROUP_BY)}"
            )

        days = max(1, min(days or DEFAULT_DAYS, 365))
        since = datetime.now(UTC) - timedelta(days=days)

        from app.models.llm_usage import LlmUsage
        from sqlalchemy import select, func, cast, String

        col = getattr(LlmUsage, group_by)
        label_expr = cast(col, String) if group_by == "project_id" else col

        stmt = (
            select(
                label_expr.label("grp"),
                func.count().label("cnt"),
                func.coalesce(func.sum(LlmUsage.tokens_in), 0).label("ti"),
                func.coalesce(func.sum(LlmUsage.tokens_out), 0).label("to"),
                func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0).label("cost"),
            )
            .where(LlmUsage.created_at >= since)
            .where(LlmUsage.success.is_(True))
            .group_by("grp")
            .order_by(func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0).desc())
        )

        async with self._sf() as session:
            rows = (await session.execute(stmt)).all()

        out: list[CostBucket] = []
        for row in rows:
            b = CostBucket()
            b.group_key = str(row.grp or "")
            b.group_label = str(row.grp or "(unknown)")
            b.calls = int(row.cnt or 0)
            b.tokens_in = int(row.ti or 0)
            b.tokens_out = int(row.to or 0)
            b.cost_estimate_usd = float(row.cost or 0.0)
            b.is_estimate = True
            out.append(b)
        return out

    async def today_total(self) -> float:
        """Today's spend from llm_usage (DB authoritative)."""
        from app.models.llm_usage import LlmUsage
        from sqlalchemy import select, func

        start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        async with self._sf() as session:
            stmt = (
                select(func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0))
                .where(LlmUsage.created_at >= start)
                .where(LlmUsage.success.is_(True))
            )
            row = (await session.execute(stmt)).one_or_none()
            return float(row[0] if row else 0.0)

    async def today_by_provider(self) -> list[dict[str, Any]]:
        """Today's cost grouped by provider — for Providers tab."""

        from app.models.llm_usage import LlmUsage
        from sqlalchemy import select, func

        start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(
                LlmUsage.provider,
                func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0).label("cost"),
                func.count().label("calls"),
            )
            .where(LlmUsage.created_at >= start)
            .where(LlmUsage.success.is_(True))
            .group_by(LlmUsage.provider)
            .order_by(func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0).desc())
        )
        async with self._sf() as session:
            rows = (await session.execute(stmt)).all()

        return [
            {
                "provider": r.provider,
                "cost_usd": float(r.cost or 0.0),
                "calls": int(r.calls or 0),
                "is_estimate": True,
            }
            for r in rows
        ]
