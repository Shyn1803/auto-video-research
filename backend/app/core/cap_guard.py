"""Daily cost cap guard — drain + enforce (Task 3-5 FR-18).

Design (BR-2 "dừng ở ranh giới node kế, không giết giữa node"):
    - This module does NOT abort in-flight LLM calls.
    - It is called at node boundaries by the pipeline runner.
    - Repo the router's usage records into llm_usage, then check cap.
    - On breach: pipeline runner sets FAILED(reason=cost_cap) + emits
      cost.cap_reached event.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("avr.cap_guard")


class CapGuardDrain:
    """Persist router usage records into llm_usage and expose daily totals."""

    def __init__(self, session_factory: Callable | None = None) -> None:
        self._sf = session_factory

    async def total_today(self) -> float:
        """Return today's accumulated cost from llm_usage (DB authoritative)."""
        if self._sf is None:
            return 0.0
        try:
            from app.models.llm_usage import LlmUsage
            from sqlalchemy import select, func

            start = datetime.now(timezone.utc).replace(
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
        except Exception as exc:
            logger.warning("cap_guard.db_query_failed: %s", exc)
            return 0.0

    async def persist(self, records: list[Any]) -> int:
        """Batch-insert usage records into llm_usage. Returns rows written."""
        if self._sf is None or not records:
            return 0

        from app.models.llm_usage import LlmUsage

        written = 0
        try:
            async with self._sf() as session:
                for rec in records:
                    row = LlmUsage(
                        created_at=_parse_ts(rec.created_at),
                        provider=rec.provider_name,
                        model="",
                        tier="",
                        task=rec.capability,
                        tokens_in=max(0, rec.tokens_used),
                        tokens_out=0,
                        cost_estimate=max(0.0, rec.cost_estimate_usd),
                        latency_ms=int(rec.latency_ms) if rec.latency_ms else None,
                        success=rec.success,
                    )
                    session.add(row)
                    written += 1
                await session.commit()
        except Exception as exc:
            logger.warning(
                "cap_guard.persist_failed after %d rows: %s", written, exc
            )
            try:
                await session.rollback()
            except Exception:
                pass
        return written

    async def check_before_node(self) -> float:
        """Return current spend; raise DailyCostCapExceeded if cap breached.

        The caller (pipeline runner):
            1. Calls this BEFORE each node.
            2. If raises: set FAILED(reason=cost_cap) + emit cost.cap_reached.
            3. Never starts the next node after breach.
        """
        from app.core.config import get_settings
        from app.core.cost_exceptions import DailyCostCapExceeded

        cap = float(get_settings().daily_cost_cap_usd)
        if cap <= 0:
            return 0.0  # cap=0 → free only; router's ALLOW_PAID already handles

        current = await self.total_today()
        if current >= cap:
            raise DailyCostCapExceeded(
                current=current,
                limit=cap,
                last_provider="(node boundary)",
            )
        return current


def _parse_ts(iso: str) -> datetime:
    if not iso:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(iso)
    except Exception:
        return datetime.now(timezone.utc)
