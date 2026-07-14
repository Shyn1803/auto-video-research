"""Event factory: cost.cap_reached (Task 3-5 BR-2).

Emitted once at the node boundary when accumulated daily spend hits DAILY_COST_CAP.
The pipeline runner listens for this to set FAILED(reason=cost_cap) and notify.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.events.schemas import EventEnvelope


SUBJECT_CAP_REACHED = "cost.cap_reached"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_cap_reached_envelope(
    *,
    correlation_id: str,
    current_spend_usd: float,
    daily_cap_usd: float,
    last_provider: str,
    run_id: str = "",
) -> EventEnvelope:
    """Build a ``cost.cap_reached`` event.

    Args:
        correlation_id: pipeline run id or project id tying this event to a run.
        current_spend_usd: accumulated spend so far today (already >= cap).
        daily_cap_usd: the configured cap that was breached.
        last_provider: provider that triggered the check before the cap fired.
        run_id: optional run identifier for observability.
    """
    return EventEnvelope(
        event_type="cost.cap_reached",
        occurred_at=_now_iso(),
        correlation_id=correlation_id,
        payload={
            "run_id": run_id,
            "current_spend_usd": round(current_spend_usd, 6),
            "daily_cap_usd": round(daily_cap_usd, 6),
            "last_provider": last_provider,
            "action": "pipeline_paused_pending_manual_resume",
        },
    )
