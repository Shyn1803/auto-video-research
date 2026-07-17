"""Admin › Costs endpoints (Task 3-5 FR-18 / BR-4).

GET  /api/admin/costs?group_by=<dim>&days=<int>   aggregated cost breakdown
GET  /api/admin/costs/daily                         today's total vs cap

RBAC: admin-only (require_role("admin")) on every route.
New endpoints — no contract change.
All cost values are estimates (BR-4): backend labels all figures is_estimate=true
so the UI can display "ước tính" next to each value.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User

logger = logging.getLogger("avr.admin.costs")

router = APIRouter(prefix="/api/admin/costs", tags=["admin: costs"])


class CostBucketResponse(BaseModel):
    group_key: str
    group_label: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_estimate_usd: float
    is_estimate: bool = True


class DailyCapResponse(BaseModel):
    cap_usd: float = 0.0
    current_usd: float = 0.0
    remaining_usd: float = 0.0
    is_estimate: bool = True


class CostsResponse(BaseModel):
    group_by: str
    days: int
    since: str
    until: str
    cap: DailyCapResponse
    buckets: list[CostBucketResponse]


def _get_session(request: Request):
    return request.app.state.database.session()


@router.get("", response_model=CostsResponse)
async def get_costs(
    request: Request,
    group_by: str = Query("task", pattern="^(task|provider|tier|model|project_id)$"),
    days: int | None = Query(30, ge=1, le=365),
    current_user: User = Depends(require_role("admin")),
):
    """Aggregated cost breakdown grouped by dimension (Task 3-5).

    Returns daily cap status alongside the buckets so the frontend can
    populate both the chart and the cap progress bar from one request.
    """
    from app.core.config import get_settings
    from app.services.cost_service import CostService

    settings = get_settings()
    sf = _get_session(request)
    svc = CostService(sf)

    window = days or 30
    since = datetime.now(UTC) - timedelta(days=window)
    until = datetime.now(UTC)

    cap_val = float(getattr(settings, "daily_cost_cap_usd", 0.0))
    today_total = await svc.today_total()
    buckets_raw = await svc.query(group_by=group_by, days=window)

    return CostsResponse(
        group_by=group_by,
        days=window,
        since=since.isoformat(),
        until=until.isoformat(),
        cap=DailyCapResponse(
            cap_usd=cap_val,
            current_usd=round(today_total, 6),
            remaining_usd=round(max(0.0, cap_val - today_total), 6),
        ),
        buckets=[
            CostBucketResponse(
                group_key=b.group_key,
                group_label=b.group_label,
                calls=b.calls,
                tokens_in=b.tokens_in,
                tokens_out=b.tokens_out,
                cost_estimate_usd=round(b.cost_estimate_usd, 6),
                is_estimate=True,
            )
            for b in buckets_raw
        ],
    )


@router.get("/daily", response_model=DailyCapResponse)
async def get_daily_cap(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Today's cap utilisation: cap / spent / remaining. All estimates (BR-4)."""
    from app.core.config import get_settings
    from app.services.cost_service import CostService

    cap = float(getattr(get_settings(), "daily_cost_cap_usd", 0.0))
    today = await CostService(_get_session(request)).today_total()
    return DailyCapResponse(
        cap_usd=cap,
        current_usd=round(today, 6),
        remaining_usd=round(max(0.0, cap - today), 6),
        is_estimate=True,
    )
