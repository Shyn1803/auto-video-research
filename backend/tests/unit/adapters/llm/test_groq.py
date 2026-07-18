"""Tests for the Groq LLM adapter (free-tier, OpenAI-compatible).

HTTP mocked with ``respx``.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.llm.groq import GroqLLM, _parse_chat_response
from app.adapters.registry import get_adapter_class, get_registered


def _settings() -> ProviderSettings:
    return ProviderSettings(
        provider_name="groq",
        api_key="groq-key-fake",
        extra={"groq_model": "llama-3.3-70b-versatile"},
    )


@pytest.fixture()
def adapter() -> GroqLLM:
    return GroqLLM(settings=_settings())


# ── Registry ──────────────────────────────────────────────────────────────────


class TestRegistryLookup:

    def test_groq_in_registry(self) -> None:
        assert get_adapter_class("llm", "groq") is GroqLLM

    def test_groq_in_get_registered(self) -> None:
        assert "groq" in get_registered("llm")

    def test_groq_is_free(self) -> None:
        assert GroqLLM.is_paid is False


# ── available() ────────────────────────────────────────────────────────────────


class TestAvailable:

    @pytest.mark.asyncio
    async def test_available_true_with_key(self) -> None:
        assert await GroqLLM(settings=_settings()).available() is True

    @pytest.mark.asyncio
    async def test_available_false_without_key(self) -> None:
        s = ProviderSettings(provider_name="groq", api_key="")
        assert await GroqLLM(settings=s).available() is False


# ── call_structured() — happy path ────────────────────────────────────────────


class TestCallStructuredHappy:

    @respx.mock
    async def test_returns_parsed_json(self, adapter: GroqLLM) -> None:
        schema = {"topic": {"type": "string"}, "relevant": {"type": "boolean"}}

        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "chatcml-1",
                    "model": "llama-3.3-70b-versatile",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    {"topic": "AI", "relevant": True}
                                ),
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )
        )

        result = await adapter.call_structured(
            prompt="Is quantum computing relevant to AI?",
            schema=schema,
            temperature=0.0,
        )
        assert result["topic"] == "AI"
        assert result["relevant"] is True

    @respx.mock
    async def test_no_key_raises(self) -> None:
        s = ProviderSettings(provider_name="groq", api_key="")
        adapter = GroqLLM(settings=s)
        with pytest.raises(ProviderError, match="no API key"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )


# ── call_structured() — error paths ───────────────────────────────────────────


class TestCallStructuredErrors:

    @respx.mock
    async def test_rate_limit_429_retryable(self, adapter: GroqLLM) -> None:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                429, json={"error": {"message": "rate limit"}}
            )
        )
        with pytest.raises(ProviderError, match="rate limited") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is True

    @respx.mock
    async def test_401_not_retryable(self, adapter: GroqLLM) -> None:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(401)
        )
        with pytest.raises(ProviderError, match="401") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is False

    @respx.mock
    async def test_malformed_json_not_retryable(self, adapter: GroqLLM) -> None:
        respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "not json!"}}
                    ]
                },
            )
        )
        with pytest.raises(ProviderError, match="not valid JSON") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is False


# ── _parse_chat_response() helper ─────────────────────────────────────────────


class TestParseChatResponse:

    def test_valid_json(self) -> None:
        raw = {
            "choices": [
                {"message": {"role": "assistant", "content": '{"a":1}'}}
            ]
        }
        assert _parse_chat_response(raw) == {"a": 1}

    def test_missing_choices_raises(self) -> None:
        with pytest.raises(ProviderError, match="missing expected fields"):
            _parse_chat_response({})
