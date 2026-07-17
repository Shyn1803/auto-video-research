"""ProviderStatusService — classify each (capability, provider) into 3-reason matrix.

BR-3 — three exact inactive reasons (Vietnamese labels: see _BADGE_LABELS):
    active                      — registered, paid gate passed, adapter.available() = True
    inactive_missing_key        — not in adapter registry
    inactive_health_failed      — registered but adapter.available() = False (or raised)
    inactive_paid_blocked       — is_paid=True and ALLOW_PAID=False

Reuses router from task 3-2: available_providers() for the matrix view,
check_health() for AC3 on-demand manual checks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("avr.provider_status")

REASON_MISSING_KEY = "inactive_missing_key"
REASON_HEALTH_FAILED = "inactive_health_failed"
REASON_PAID_BLOCKED = "inactive_paid_blocked"
STATUS_ACTIVE = "active"

_BADGE_LABELS: dict[str, str] = {
    STATUS_ACTIVE: "Đang hoạt động",
    REASON_MISSING_KEY: "Thiếu key",
    REASON_HEALTH_FAILED: "Kiểm tra thất bại",
    REASON_PAID_BLOCKED: "Bị chặn trả phí",
}

_KNOWN_CAPABILITIES = [
    "llm",
    "tts",
    "search",
    "image_gen",
    "asset_stock",
    "storage",
    "publish",
]


class ProviderStatusEntry:
    """Single (capability, provider) status row for the Admin matrix."""

    __slots__ = (
        "capability",
        "provider",
        "status",
        "reason_detail",
        "last_checked_at",
        "cost_today_usd",
        "chain_position",
    )

    def __init__(
        self,
        capability: str = "",
        provider: str = "",
        status: str = STATUS_ACTIVE,
        reason_detail: str = "",
        last_checked_at: datetime | None = None,
        cost_today_usd: float = 0.0,
        chain_position: int = 0,
    ) -> None:
        self.capability = capability
        self.provider = provider
        self.status = status
        self.reason_detail = reason_detail
        self.last_checked_at = last_checked_at
        self.cost_today_usd = cost_today_usd
        self.chain_position = chain_position

    @property
    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE

    @property
    def badge_label(self) -> str:
        return _BADGE_LABELS.get(self.status, self.status)


class ProviderStatusService:
    """Build the (capability x provider) status matrix for the Providers tab."""

    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory

    async def get_matrix(self) -> list[ProviderStatusEntry]:
        """Return one entry per known (capability, provider) pair in chain order."""

        from app.adapters.registry import get_adapter_class
        from app.core.config import get_settings
        from app.core.router import ProviderRouter

        settings = get_settings()
        router = ProviderRouter()
        entries: list[ProviderStatusEntry] = []

        for capability in _KNOWN_CAPABILITIES:
            chain: list[str] = router.get_chain(capability)
            seen_cls: set[type] = set()

            for position, provider_name in enumerate(chain):
                cls = get_adapter_class(capability, provider_name)

                # Step 1: not registered?
                if cls is None:
                    entries.append(ProviderStatusEntry(
                        capability=capability, provider=provider_name,
                        status=REASON_MISSING_KEY,
                        reason_detail="provider not registered",
                        chain_position=position,
                    ))
                    continue

                # Skip duplicate adapter classes (aliases resolve to same class)
                if cls in seen_cls:
                    continue
                seen_cls.add(cls)

                # Step 2: paid gate (BR-1) — never trust adapter alone
                is_paid = getattr(cls, "is_paid", True)
                if is_paid and not getattr(settings, "allow_paid", False):
                    entries.append(ProviderStatusEntry(
                        capability=capability, provider=provider_name,
                        status=REASON_PAID_BLOCKED,
                        reason_detail="ALLOW_PAID=false; provider is paid",
                        chain_position=position,
                    ))
                    continue

                # Step 3: availability check via router (uses 30 s cache)
                alive: bool = False
                detail: str = "available() returned False"
                try:
                    healthy = router.available_providers(capability)
                    alive = any(a.name == provider_name for a in healthy)
                except Exception as exc:
                    alive = False
                    detail = str(exc)[:200]

                if alive:
                    cost_today = 0.0
                    if self._sf is not None:
                        try:
                            cost_today = await _today_cost(self._sf, provider_name)
                        except Exception:
                            pass
                    entries.append(ProviderStatusEntry(
                        capability=capability, provider=provider_name,
                        status=STATUS_ACTIVE,
                        last_checked_at=datetime.now(timezone.utc),
                        cost_today_usd=cost_today,
                        chain_position=position,
                    ))
                else:
                    entries.append(ProviderStatusEntry(
                        capability=capability, provider=provider_name,
                        status=REASON_HEALTH_FAILED,
                        reason_detail=detail,
                        last_checked_at=datetime.now(timezone.utc),
                        chain_position=position,
                    ))

        return entries

    async def health_check(
        self,
        capability: str,
        provider_name: str,
    ) -> ProviderStatusEntry:
        """On-demand health check for a single provider (AC3).

        Forces a fresh ``adapter.available()`` call — bypasses the 30s cache.
        When the service recovers, the next manual check reflects it immediately
        (no stale data — AC3).
        """
        from app.adapters.registry import get_adapter_class
        from app.core.config import get_settings
        from app.core.router import ProviderRouter

        settings = get_settings()
        checked = datetime.now(timezone.utc)

        # Gate 1: not registered?
        cls = get_adapter_class(capability, provider_name)
        if cls is None:
            return ProviderStatusEntry(
                capability=capability, provider=provider_name,
                status=REASON_MISSING_KEY,
                reason_detail="provider not registered",
                last_checked_at=checked,
            )

        # Gate 2: paid payment blocked?
        is_paid = getattr(cls, "is_paid", True)
        if is_paid and not getattr(settings, "allow_paid", False):
            return ProviderStatusEntry(
                capability=capability, provider=provider_name,
                status=REASON_PAID_BLOCKED,
                reason_detail="ALLOW_PAID=false; provider is paid",
                last_checked_at=checked,
            )

        # Gate 3: fresh health check
        router = ProviderRouter()
        try:
            ok = await router.check_health(capability, provider_name)
        except Exception as exc:
            ok = False
            detail = str(exc)[:200]
        else:
            detail = "" if ok else "available() returned False"

        return ProviderStatusEntry(
            capability=capability, provider=provider_name,
            status=STATUS_ACTIVE if ok else REASON_HEALTH_FAILED,
            reason_detail=detail,
            last_checked_at=checked,
        )


# ── internal helpers ──────────────────────────────────────────────────────────


async def _today_cost(
    session_factory: Any,
    provider_name: str,
) -> float:
    """Return today's cost estimate for a single provider from llm_usage."""

    from app.models.llm_usage import LlmUsage
    from sqlalchemy import select, func

    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    async with session_factory() as session:
        stmt = (
            select(func.coalesce(func.sum(LlmUsage.cost_estimate), 0.0))
            .where(LlmUsage.provider == provider_name)
            .where(LlmUsage.created_at >= start)
            .where(LlmUsage.success.is_(True))
        )
        row = (await session.execute(stmt)).one_or_none()
        return float(row[0] if row else 0.0)
