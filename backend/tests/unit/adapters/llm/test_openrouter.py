"""Tests for OpenRouter free/paid adapter split (BR-4).

HTTP mocked with respx.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.llm.openrouter import (
    OpenRouterFreeLLM,
    OpenRouterPaidLLM,
    _is_free_model,
)
from app.adapters.registry import get_adapter_class, get_registered


def _s(variant: str = "openrouter_free", **extra: str) -> ProviderSettings:
    base: dict[str, str] = {}
    if variant == "openrouter_free":
        base["openrouter_free_model"] = "google/gemini-2.0-flash-exp:free"
    else:
        base["openrouter_paid_model"] = ""
    return ProviderSettings(provider_name=variant, api_key="or-fake-key", extra=base | extra)


class TestIsFreeModel:
    def test_free_model_returns_true(self) -> None:
        assert _is_free_model("google/gemini-2.0-flash-exp:free") is True

    def test_paid_model_returns_false(self) -> None:
        assert _is_free_model("openai/gpt-4o") is False

    def test_empty_string_returns_false(self) -> None:
        assert _is_free_model("") is False


class TestRegistryLookup:
    def test_openrouter_free_in_registry(self) -> None:
        assert get_adapter_class("llm", "openrouter_free") is OpenRouterFreeLLM

    def test_openrouter_paid_in_registry(self) -> None:
        assert get_adapter_class("llm", "openrouter_paid") is OpenRouterPaidLLM

    def test_openrouter_free_is_not_paid(self) -> None:
        assert OpenRouterFreeLLM.is_paid is False

    def test_openrouter_paid_is_paid(self) -> None:
        assert OpenRouterPaidLLM.is_paid is True


class TestFreeModelFilter:
    @respx.mock
    async def test_openrouter_free_sends_free_model(self) -> None:
        adapter = OpenRouterFreeLLM(settings=_s())
        route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps({"text": "ok"}),
                            }
                        }
                    ]
                },
            )
        )
        await adapter.call_structured("hi", {"text": {"type": "string"}})
        body = json.loads(route.calls.last.request.content)
        assert body["model"].endswith(":free")


class TestAvailable:
    async def test_free_available_with_key(self) -> None:
        assert await OpenRouterFreeLLM(settings=_s()).available() is True

    async def test_paid_available_with_key(self) -> None:
        assert await OpenRouterPaidLLM(settings=_s("openrouter_paid")).available() is True

    async def test_paid_not_available_without_key(self) -> None:
        s = ProviderSettings(
            provider_name="openrouter_paid",
            api_key="",
            extra={"openrouter_paid_model": "anthropic/claude-sonnet-5"},
        )
        assert await OpenRouterPaidLLM(settings=s).available() is False
