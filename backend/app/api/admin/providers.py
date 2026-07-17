"""Admin › Providers endpoints (Task 3-5 BR-3 / BR-4 / AC3).

GET  /api/admin/providers               capability x provider status matrix
GET  /api/admin/providers/tab           single-call full tab page data
POST /api/admin/providers/{n}/health-check  on-demand health check (AC3)
GET  /api/admin/providers/today         today cost per provider (BR-4: all estimates)

RBAC: admin-only (require_role("admin") on every route).
No contract change — new endpoints only.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.deps import require_role
from app.models.user import User

logger = logging.getLogger("avr.admin.providers")

router = APIRouter(prefix="/api/admin/providers", tags=["admin: providers"])


# ── Response models ────────────────────────────────────────────────────────────


class ProviderMatrixResponse(BaseModel):
    capability: str
    provider: str
    status: str
    badge_label: str
    reason_detail: str | None = None
    last_checked_at: str | None = None
    cost_today_usd: float = 0.0
    is_estimate: bool = True
    chain_position: int = 0


class HealthCheckResponse(BaseModel):
    capability: str
    provider: str
    status: str
    badge_label: str
    reason_detail: str | None = None
    last_checked_at: str | None = None


class TodayCostItem(BaseModel):
    provider: str
    cost_usd: float
    calls: int
    is_estimate: bool = True


class DailyCapInfo(BaseModel):
    cap_usd: float = 0.0
    current_usd: float = 0.0
    remaining_usd: float = 0.0
    is_estimate: bool = True


class ProvidersTabData(BaseModel):
    cap: DailyCapInfo
    matrix: list[ProviderMatrixResponse]
    today_by_provider: list[TodayCostItem] | None = None


# ── helpers ────────────────────────────────────────────────────────────────────


def _get_session(request: Request):
    return request.app.state.database.session()


def _fmt_dt(dt: Any) -> str | None:
    return dt.isoformat() if dt else None


def _to_matrix(e: Any) -> ProviderMatrixResponse:
    return ProviderMatrixResponse(
        capability=e.capability,
        provider=e.provider,
        status=e.status,
        badge_label=e.badge_label,
        reason_detail=e.reason_detail or None,
        last_checked_at=_fmt_dt(e.last_checked_at),
        cost_today_usd=round(e.cost_today_usd or 0.0, 6),
        is_estimate=True,
        chain_position=e.chain_position,
    )


# ── endpoints ──────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProviderMatrixResponse])
async def list_provider_status(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Full matrix: capability x provider, 3-reason inactive labels (BR-3)."""
    from app.services.provider_status_service import (
        REASON_MISSING_KEY,
        ProviderStatusEntry,
        ProviderStatusService,
    )

    svc = ProviderStatusService(session_factory=_get_session(request))
    raw = await svc.get_matrix()

    return [_to_matrix(e) for e in raw]


@router.post(
    "/{provider_name}/health-check",
    response_model=HealthCheckResponse,
)
async def health_check_provider(
    provider_name: str,
    request: Request,
    capability: str | None = Query(  # type: ignore[assignment]
        default=None,
        description=(
            "Capability box (llm|tts|search|image_gen|asset_stock|storage|publish). "
            "Omit to auto-detect from adapter registry."
        ),
    ),
    current_user: User = Depends(require_role("admin")),
):
    """On-demand health check for a single provider (AC3 / BR-3).

    Forces a fresh ``adapter.available()`` call — bypasses the 30s cache.
    When the service recovers this manual call reflects it immediately (AC3).
    """
    from app.services.provider_status_service import (
        ProviderStatusService,
        REASON_MISSING_KEY,
        ProviderStatusEntry,
    )

    svc = ProviderStatusService(session_factory=_get_session(request))

    if capability:
        entry = await svc.health_check(capability, provider_name)
    else:
        # Auto-detect: scan the registry for which capability owns this provider.
        from app.adapters.registry import get_registered

        all_caps = (
            "llm",
            "tts",
            "search",
            "image_gen",
            "asset_stock",
            "storage",
            "publish",
        )
        matched = [
            c
            for c in all_caps
            if any(n == provider_name for n in get_registered(c))
        ]
        if matched:
            entry = await svc.health_check(matched[0], provider_name)
        else:
            entry = ProviderStatusEntry(
                capability="unknown",
                provider=provider_name,
                status=REASON_MISSING_KEY,
                reason_detail="provider not registered in any capability",
            )

    return HealthCheckResponse(
        capability=entry.capability,
        provider=entry.provider,
        status=entry.status,
        badge_label=entry.badge_label,
        reason_detail=entry.reason_detail or None,
        last_checked_at=_fmt_dt(entry.last_checked_at),
    )


@router.get("/tab", response_model=ProvidersTabData)
async def providers_tab_data(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Single-call full Providers tab data (matrix + cap + today-by-provider)."""
    from app.core.config import get_settings
    from app.services.cost_service import CostService
    from app.services.provider_status_service import ProviderStatusService

    settings = get_settings()
    sf = _get_session(request)
    cost_svc = CostService(sf)
    status_svc = ProviderStatusService(session_factory=sf)

    cap_val = float(getattr(settings, "daily_cost_cap_usd", 0))
    today_total = await cost_svc.today_total()

    return ProvidersTabData(
        cap=DailyCapInfo(
            cap_usd=cap_val,
            current_usd=round(today_total, 6),
            remaining_usd=round(max(0.0, cap_val - today_total), 6),
        ),
        matrix=[_to_matrix(e) for e in await status_svc.get_matrix()],
        today_by_provider=[
            TodayCostItem(
                provider=p["provider"],
                cost_usd=p["cost_usd"],
                calls=p["calls"],
                is_estimate=p["is_estimate"],
            )
            for p in await cost_svc.today_by_provider()
        ],
    )


@router.get("/today", response_model=list[TodayCostItem])
async def today_cost_by_provider(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Today's cost per provider — all figures are estimates (BR-4)."""
    from app.services.cost_service import CostService

    return [
        TodayCostItem(
            provider=r["provider"],
            cost_usd=r["cost_usd"],
            calls=r["calls"],
            is_estimate=r["is_estimate"],
        )
        for r in await CostService(_get_session(request)).today_by_provider()
    ]
