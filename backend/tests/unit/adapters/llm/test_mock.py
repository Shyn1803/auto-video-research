"""Tests for the Mock LLM adapter (BR-2: APP_ENV=production guard).

Hard-guards that mock returns deterministic fixtures in dev/test and
raises in production.
"""

from __future__ import annotations

import os

import pytest
from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.llm.mock import MockLLM, _build_stub
from app.adapters.registry import get_adapter_class, get_registered


def _settings(env: str = "development") -> ProviderSettings:
    return ProviderSettings(
        provider_name="mock",
        api_key="mock-key",
        extra={"mock_env": env},
    )


# ── Registry ──────────────────────────────────────────────────────────────────


class TestRegistryLookup:

    def test_mock_in_registry(self) -> None:
        assert get_adapter_class("llm", "mock") is MockLLM

    def test_mock_in_get_registered(self) -> None:
        assert "mock" in get_registered("llm")


# ── BR-2: APP_ENV=production raises ──────────────────────────────────────────


class TestProductionGuard:

    def test_available_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "environ", {"APP_ENV": "production"})
        adapter = MockLLM(settings=_settings())
        with pytest.raises(ProviderError, match="not available in APP_ENV=production"):
            import asyncio
            asyncio.run(adapter.available())

    def test_call_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "environ", {"APP_ENV": "production"})
        adapter = MockLLM(settings=_settings())
        with pytest.raises(ProviderError, match="not available in APP_ENV=production"):
            import asyncio
            asyncio.run(
                adapter.call_structured("test", {"x": {"type": "string"}})
            )

    def test_not_available_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "environ", {"APP_ENV": "development"})
        adapter = MockLLM(settings=_settings())
        import asyncio
        assert asyncio.run(adapter.available()) is True

    def test_not_available_in_test_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "environ", {"APP_ENV": "test"})
        adapter = MockLLM(settings=_settings())
        import asyncio
        assert asyncio.run(adapter.available()) is True


# ── Fixture matching ──────────────────────────────────────────────────────────


class TestFixtures:

    def test_summarize_fixture(self) -> None:
        adapter = MockLLM(settings=_settings())
        import asyncio
        result = asyncio.run(
            adapter.call_structured(
                "summarize this article", {"summary": {"type": "string"}}
            )
        )
        assert "summary" in result
        assert isinstance(result["summary"], str)

    def test_fact_check_fixture(self) -> None:
        adapter = MockLLM(settings=_settings())
        import asyncio
        result = asyncio.run(
            adapter.call_structured(
                "fact_check the following claims",
                {"claims": {"type": "array"}},
            )
        )
        assert "claims" in result

    def test_script_fixture(self) -> None:
        adapter = MockLLM(settings=_settings())
        import asyncio
        result = asyncio.run(
            adapter.call_structured(
                "write a video script", {"scenes": {"type": "array"}}
            )
        )
        assert "scenes" in result
        assert len(result["scenes"]) == 2

    def test_no_fixture_falls_back_to_stub(self) -> None:
        adapter = MockLLM(settings=_settings())
        import asyncio
        result = asyncio.run(
            adapter.call_structured(
                "translate to English",
                {"translation": {"type": "string"}, "score": {"type": "number"}},
            )
        )
        # Falls back to _build_stub — keyed by schema keys
        assert "translation" in result
        assert "score" in result

    def test_fixture_is_deterministic_across_calls(self) -> None:
        adapter = MockLLM(settings=_settings())
        import asyncio
        r1 = asyncio.run(adapter.call_structured("summarize: test", {"x": {"type": "string"}}))
        r2 = asyncio.run(adapter.call_structured("summarize: test", {"x": {"type": "string"}}))
        assert r1 == r2


# ── _build_stub helper ────────────────────────────────────────────────────────


class TestBuildStub:

    def test_all_primitive_types(self) -> None:
        schema = {
            "text": {"type": "string"},
            "count": {"type": "integer"},
            "score": {"type": "number"},
            "active": {"type": "boolean"},
            "tags": {"type": "array"},
        }
        result = _build_stub(schema)
        assert result["text"] == "[mock:text]"
        assert result["count"] == 42
        assert result["score"] == 42.0
        assert result["active"] is True
        assert result["tags"] == []

    def test_unknown_type_defaults_to_string_stub(self) -> None:
        schema = {"custom": {"type": "object", "properties": {}}}
        result = _build_stub(schema)
        assert result["custom"] == "[mock:custom]"

    def test_plain_value_schema_keys(self) -> None:
        """Schema key whose value is not a dict → string stub."""
        schema = {"plain": "something"}
        result = _build_stub(schema)
        assert result["plain"] == "[mock:plain]"
