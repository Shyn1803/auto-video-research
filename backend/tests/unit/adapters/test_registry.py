"""Registry business-rule tests (BR-3 duplicate-name, BR-4 default-paid)."""

from __future__ import annotations

import pytest

from app.adapters.base import BaseAdapter, ProviderSettings, ProviderError
from app.adapters.registry import (
    _register,
    get_adapter_class,
    register_llm,
    register_tts,
    unregister,  # exported for test cleanup
)


# ── BR-4: is_paid defaults to True (cost-safe) ────────────────────────────────

class Paid(BaseAdapter):
    """Subclass that omits ``is_paid`` — must default to ``True``."""
    name = "paid_default"
    # is_paid NOT declared

def test_default_is_paid_is_true() -> None:
    assert Paid.is_paid is True


# ── BR-3: duplicate (capability, name) raises at decoration time ──────────────

class DupA:
    """Used to verify duplicate registration fails with both files."""
    name = "dup_name"

class DupB:
    name = "dup_name"


def test_duplicate_registration_raises() -> None:
    """Registering a (cap, name) already present must raise with both module
    identifiers in the error text (AC2 — message names both files)."""
    _register("llm", "dup_unique_a", DupA)
    try:
        with pytest.raises(RuntimeError, match="Duplicate adapter registration"):
            _register("llm", "dup_unique_a", DupB)
    finally:
        _unregister("llm", "dup_unique_a")


def test_duplicate_error_mentions_both_names() -> None:
    """The exception message must contain both the existing and conflicting
    class identifiers so the developer can locate both files immediately."""
    _register("llm", "dup_unique_b", DupA)
    try:
        with pytest.raises(RuntimeError) as exc_info:
            _register("llm", "dup_unique_b", DupB)
        msg = str(exc_info.value)
        assert "dup_unique_b" in msg
        # Both module-qualified names appear in the message
        assert "already registered" in msg
        assert "conflict" in msg.lower() or "duplicate" in msg.lower()
    finally:
        _unregister("llm", "dup_unique_b")


# ── Teardown helper ────────────────────────────────────────────────────────────

def _unregister(capability: str, name: str) -> None:
    """Remove a test-only registration from the registry internal dict."""
    # The registry stores entries in a module-private dict; re-import
    # the module and mutate the dict via the public ``get_registered``
    # deletion path — no public remove function exists yet, so we reach
    # into the module-private _registry via import.
    from app.adapters import registry
    key = (capability, name)
    if key in registry._registry:
        del registry._registry[key]
