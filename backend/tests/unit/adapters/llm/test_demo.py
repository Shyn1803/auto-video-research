"""Tests for the demo LLM adapter (copy-paste template, AC1).

No network call in any test -- the demo adapter is a pure stub.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.adapters.base import ProviderSettings, ProviderError
from app.adapters.llm.demo import DemoLLM
from app.adapters.registry import get_adapter_class, get_registered


def _settings() -> ProviderSettings:
    return ProviderSettings(provider_name="demo", api_key="demo-key-123")


# ── AC1: 1 file + decorator -> registry, callable via router mock ───────────


class TestRegistryLookup:
    def test_demo_adapter_in_registry(self) -> None:
        assert get_adapter_class("llm", "demo") is DemoLLM

    def test_demo_in_get_registered(self) -> None:
        assert "demo" in get_registered("llm")

    def test_demo_name_and_paid(self) -> None:
        assert DemoLLM.name == "demo"
        assert DemoLLM.is_paid is False


class TestDemoAdapter:
    @pytest.mark.asyncio
    async def test_available_with_key(self) -> None:
        assert await DemoLLM(settings=_settings()).available() is True

    @pytest.mark.asyncio
    async def test_call_structured_returns_dict(self) -> None:
        adapter = DemoLLM(settings=_settings())
        result = await adapter.call_structured(
            prompt="Hello",
            schema={"answer": {"type": "string"}, "confidence": {"type": "number"}},
        )
        assert isinstance(result, dict)
        assert "answer" in result


class TestConfigGuard:
    @pytest.mark.asyncio
    async def test_no_key_raises_provider_error(self) -> None:
        adapter = DemoLLM(settings=ProviderSettings(provider_name="demo"))
        with pytest.raises(ProviderError, match="no api_key"):
            await adapter.call_structured(
                prompt="test", schema={"x": {"type": "string"}}
            )
