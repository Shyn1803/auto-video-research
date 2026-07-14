"""Unit tests for ProviderStatusService — Task 3-5 AC1, AC3.

Tests with mocks only — no live adapters, no DB.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault(
    "FERNET_MASTER_KEY",
    "zQmXJvKpL3nR7sT9wY2aB5cD8fG1hJ4kM6nP0qR2tU5vW8xA=",
)

from app.services.provider_status_service import (
    REASON_HEALTH_FAILED,
    REASON_MISSING_KEY,
    REASON_PAID_BLOCKED,
    STATUS_ACTIVE,
    _BADGE_LABELS,
    ProviderStatusEntry,
    ProviderStatusService,
)


# ── Badge label tests ──────────────────────────────────────────────────────────


class TestBadgeLabels:
    def test_four_labels(self):
        assert _BADGE_LABELS[STATUS_ACTIVE] == "Đang hoạt động"
        assert _BADGE_LABELS[REASON_MISSING_KEY] == "Thiếu key"
        assert _BADGE_LABELS[REASON_HEALTH_FAILED] == "Kiểm tra thất bại"
        assert _BADGE_LABELS[REASON_PAID_BLOCKED] == "Bị chặn trả phí"

    def test_entry_is_active(self):
        assert ProviderStatusEntry("c", "p", STATUS_ACTIVE).is_active
        assert not ProviderStatusEntry("c", "p", REASON_MISSING_KEY).is_active
        assert not ProviderStatusEntry("c", "p", REASON_HEALTH_FAILED).is_active
        assert not ProviderStatusEntry("c", "p", REASON_PAID_BLOCKED).is_active


# ── AC1: 3 env scenarios ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ac1_zero_keys_scenario():
    """Scenario 1 (0 key): unregistered provider → inactive_missing_key.

    Patches ProviderRouter to yield a provider not in the registry.
    """
    import app.core.router as _router_mod
    from app.core.router import ProviderRouter

    original_init = ProviderRouter.__init__

    def _fake_init(self):
        self._settings = MagicMock()
        self._settings.allow_paid = False
        self._settings.__getattr__ = lambda _, n: ""
        self._availability = {}
        self._circuit_open_until = {}
        self._cb_event_sent = set()
        self._usage = []
        self._cap_guard = None

    def _fake_chain(self, capability, tier=""):
        return ["provider_not_registered_123"]

    ProviderRouter.__init__ = _fake_init  # type: ignore
    ProviderRouter.get_chain = _fake_chain  # type: ignore

    try:
        svc = ProviderStatusService(session_factory=None)
        entries = await svc.get_matrix()
    finally:
        ProviderRouter.__init__ = original_init  # type: ignore
        del ProviderRouter.get_chain

    assert any(
        e.provider == "provider_not_registered_123"
        and e.status == REASON_MISSING_KEY
        for e in entries
    ), f"Got: {[(e.provider, e.status) for e in entries]}"


@pytest.mark.asyncio
async def test_ac1_paid_blocked_scenario():
    """Scenario 2 (free keys only): is_paid=True + ALLOW_PAID=False → inactive_paid_blocked.

    Registers a paid adapter in the real registry temporarily, patches the router.
    """
    import app.core.router as _router_mod
    from app.core.router import ProviderRouter
    from app.adapters.base import BaseAdapter
    from app.adapters.registry import (
        register_llm,
        _REGISTRY,
    )

    unique_name = "_test_ac1_paidblock_llm"

    class _PaidBlock(BaseAdapter):
        name = unique_name
        is_paid = True
        async def available(self):
            return True

    register_llm(unique_name, _PaidBlock)

    original_init = ProviderRouter.__init__

    def _fake_init(self):
        self._settings = MagicMock()
        self._settings.allow_paid = False
        self._settings.__getattr__ = lambda _, n: ""
        self._availability = {}
        self._circuit_open_until = {}
        self._cb_event_sent = set()
        self._usage = []
        self._cap_guard = None

    def _fake_chain(self, capability, tier=""):
        return [unique_name]

    ProviderRouter.__init__ = _fake_init  # type: ignore
    ProviderRouter.get_chain = _fake_chain  # type: ignore

    # Mock available_providers to include our adapter
    def _fake_available(self, capability, tier=""):
        from app.adapters.registry import get_adapter_class
        cls = get_adapter_class("llm", unique_name)
        if cls:
            m = MagicMock()
            m.name = unique_name
            return [m]
        return []

    ProviderRouter.available_providers = _fake_available  # type: ignore

    try:
        svc = ProviderStatusService(session_factory=None)
        entries = await svc.get_matrix()
    finally:
        ProviderRouter.__init__ = original_init  # type: ignore
        del ProviderRouter.get_chain  # type: ignore
        del ProviderRouter.available_providers  # type: ignore
        _REGISTRY.pop(("llm", unique_name), None)

    matching = [e for e in entries if e.provider == unique_name]
    assert matching, f"expected {unique_name} in matrix; got {[e.provider for e in entries]}"
    assert matching[0].status == REASON_PAID_BLOCKED
    assert matching[0].badge_label == "Bị chặn trả phí"


@pytest.mark.asyncio
async def test_ac1_active_scenario():
    """Scenario 3 (full + paid): registered, paid allowed, available → active."""

    import app.core.router as _router_mod
    from app.core.router import ProviderRouter
    from app.adapters.base import BaseAdapter
    from app.adapters.registry import register_llm, _REGISTRY

    unique_name = "_test_ac1_active_llm"

    class _Active(BaseAdapter):
        name = unique_name
        is_paid = False  # free adapter so no paid gate to trip us
        async def available(self):
            return True

    register_llm(unique_name, _Active)

    original_init = ProviderRouter.__init__

    def _fake_init(self):
        self._settings = MagicMock()
        self._settings.allow_paid = True
        self._settings.__getattr__ = lambda _, n: ""
        self._availability = {}
        self._circuit_open_until = {}
        self._cb_event_sent = set()
        self._usage = []
        self._cap_guard = None

    def _fake_chain(self, capability, tier=""):
        return [unique_name]

    def _fake_available(self, capability, tier=""):
        m = MagicMock()
        m.name = unique_name
        return [m]

    ProviderRouter.__init__ = _fake_init  # type: ignore
    ProviderRouter.get_chain = _fake_chain  # type: ignore
    ProviderRouter.available_providers = _fake_available  # type: ignore

    try:
        svc = ProviderStatusService(session_factory=None)
        entries = await svc.get_matrix()
    finally:
        ProviderRouter.__init__ = original_init  # type: ignore
        del ProviderRouter.get_chain  # type: ignore
        del ProviderRouter.available_providers  # type: ignore
        _REGISTRY.pop(("llm", unique_name), None)

    matching = [e for e in entries if e.provider == unique_name]
    assert matching, f"expected {unique_name} in matrix"
    assert matching[0].status == STATUS_ACTIVE
    assert matching[0].badge_label == "Đang hoạt động"


# ── AC3: health-check reflects reality ────────────────────────────────────────


@pytest.mark.asyncio
async def test_ac3_health_check_directly_reflects_adapter_state():
    """AC3: manual health_check call reflects the adapter state without stale cache."""

    import app.core.router as _router_mod
    from app.core.router import ProviderRouter
    from app.adapters.base import BaseAdapter
    from app.adapters.registry import register_llm, _REGISTRY

    unique_name = "_test_ac3_llm"

    class _AC3(BaseAdapter):
        name = unique_name
        is_paid = False
        async def available(self):
            return True

    register_llm(unique_name, _AC3)

    original_init = ProviderRouter.__init__
    original_check_health = ProviderRouter.check_health

    state = {"ok": True}

    def _fake_init(self):
        self._settings = MagicMock()
        self._settings.allow_paid = True
        self._settings.__getattr__ = lambda _, n: ""
        self._availability = {}
        self._circuit_open_until = {}
        self._cb_event_sent = set()
        self._usage = []
        self._cap_guard = None

    def _fake_chain(self, capability, tier=""):
        return [unique_name]

    async def _toggleable_check(self, c, p):
        return state["ok"]

    ProviderRouter.__init__ = _fake_init  # type: ignore
    ProviderRouter.get_chain = _fake_chain  # type: ignore
    ProviderRouter.check_health = _toggleable_check  # type: ignore

    try:
        svc = ProviderStatusService(session_factory=None)

        # 1. Healthy → active
        e1 = await svc.health_check("llm", unique_name)
        assert e1.status == STATUS_ACTIVE

        # 2. Outage → health_failed
        state["ok"] = False
        e2 = await svc.health_check("llm", unique_name)
        assert e2.status == REASON_HEALTH_FAILED
        assert e2.badge_label == "Kiểm tra thất bại"

        # 3. Recovery → active (no stale cache bypass)
        state["ok"] = True
        e3 = await svc.health_check("llm", unique_name)
        assert e3.status == STATUS_ACTIVE

    finally:
        ProviderRouter.__init__ = original_init  # type: ignore
        ProviderRouter.check_health = original_check_health  # type: ignore
        del ProviderRouter.get_chain  # type: ignore
        _REGISTRY.pop(("llm", unique_name), None)
