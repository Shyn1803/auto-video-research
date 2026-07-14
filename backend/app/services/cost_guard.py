"""Daily cost guard — pre-call cap check (Task 3-5 BR-1 / BR-2).

Usage:
    guard = CostGuard(db_session_factory, router_usage)
    await guard.before_call(cost_estimate_usd, provider_name, correlation_id)

Raises:
    DailyCostCapExceeded: when the new total would breach DAILY_COST_CAP.

The guard is deliberately a thin side-effecting module (no business logic).
The pipeline runner catches DailyCostCapExceeded, waits for the current
node to finish (BR-2 — "dừng ở ranh giới node kế, không giết giữa node"),
then emits ``cost.cap_reached`` and sets status FAILED(reason=cost_cap).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from app.core.config import get_settings
from app.core.cost_exceptions import DailyCostCapExceeded

logger = logging.getLogger("avr.cost_guard")


class CostGuard:
    """Pre-call cost accumulator.

    The in-memory accumulator mirrors the most recent router usage records.
    It is intentionally shallow — on process restart the DB becomes the
    source of truth (see ``_today_cost`` fallback below).
    """

    def __init__(
        self,
        session_factory: Callable[[], Any] | None = None,
        usage_records: list[Any] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._usage_records = usage_records or []
        self._settings = get_settings()
        # in-memory accumulator for the current process run
        self._accumulated: float = 0.0

    # ── public ─────────────────────────────────────────────────────────

    async def before_call(
        self,
        cost_estimate: float,
        provider_name: str,
        correlation_id: str = "",
    ) -> None:
        """Raise if accepting *cost_estimate* would breach the daily cap.

        Call BEFORE the actual provider invocation — if this raises, the
        caller skips the call and falls over to cost-cap handling.
        """
        cap = self._settings.daily_cost_cap_usd
        if cap <= 0:
            # cap=0 means "free only" but we do not block here because
            # the payment gate (ALLOW_PAID) already filters paid providers
            # out before they reach the router. A cap of 0 with a free-only
            # chain is simply unrestricted.
            return
        current = self._accumulated + cost_estimate
        logger.info(
            "cost_guard.check cap=%.4f current=%.4f provider=%s",
            cap,
            current,
            provider_name,
        )
        if current > cap:
            raise DailyCostCapExceeded(
                current=current,
                limit=cap,
                last_provider=provider_name,
            )

    def record(self, cost_estimate: float) -> None:
        """Record a completed call after it succeeds."""

        self._accumulated += cost_estimate
        logger.debug(
            "cost_guard.record accum=%.4f cap=%.4f",
            self._accumulated,
            self._settings.daily_cost_cap_usd,
        )

    def reset(self) -> None:
        """Reset the in-memory accumulator (call at midnight UTC)."""

        self._accumulated = 0.0

    def current_spend(self) -> float:
        """Return today's accumulated spend (in-memory)."""

        return self._accumulated

    async def today_cost_from_db(self) -> float:
        """Query llm_usage for today's total — authoritative post-restart."""

        if self._session_factory is None:
            return 0.0
        try:
            from app.models.llm_usage import LlmUsage
            from sqlalchemy import select, func
            from datetime import date

            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            async with self._session_factory() as session:
                stmt = (
                    select(func.coalesce(func.sum(LlmUsage.cost_estimate), 0))
                    .where(LlmUsage.created_at >= today_start)
                    .where(LlmUsage.success.is_(True))
                )
                result = await session.execute(stmt)
                total = float(result.scalar() or 0)
                self._accumulated = total
                return total
        except Exception as exc:
            logger.warning("cost_guard.db_query_failed: %s", exc)
            return self._accumulated
