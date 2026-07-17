"""Tests for the Gemini LLM adapter.

HTTP mocked with ``respx`` — no live network calls.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.llm.gemini import GeminiLLM, _build_gemini_body, _parse_gemini_response
from app.adapters.registry import get_adapter_class, get_registered


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _settings(extra: dict[str, str] | None = None) -> ProviderSettings:
    base: dict[str, str] = {
        "gemini_model": "gemini-flash-latest",
    }
    if extra:
        base |= extra
    return ProviderSettings(
        provider_name="gemini",
        api_key="fake-gemini-key",
        extra=base,
    )


@pytest.fixture()
def adapter() -> GeminiLLM:
    return GeminiLLM(settings=_settings())


# ── Registry ──────────────────────────────────────────────────────────────────


class TestRegistryLookup:

    def test_gemini_in_registry(self) -> None:
        assert get_adapter_class("llm", "gemini") is GeminiLLM

    def test_gemini_in_get_registered(self) -> None:
        assert "gemini" in get_registered("llm")

    def test_gemini_is_free(self) -> None:
        assert GeminiLLM.is_paid is False


# ── available() ────────────────────────────────────────────────────────────────


class TestAvailable:

    async def test_available_true_with_key(self) -> None:
        s = _settings()
        assert await GeminiLLM(settings=s).available() is True

    async def test_available_false_without_key(self) -> None:
        s = ProviderSettings(
            provider_name="gemini", api_key="", extra={"gemini_model": "flash"}
        )
        assert await GeminiLLM(settings=s).available() is False


# ── call_structured() — happy path ────────────────────────────────────────────


class TestCallStructuredHappy:

    @respx.mock
    async def test_returns_parsed_json(self, adapter: GeminiLLM) -> None:
        schema = {"answer": {"type": "string"}, "confidence": {"type": "number"}}

        respx.post(
            "https://generativelanguage.googleapis.com",
            path__regex=r"^/v1beta/models/.+:generateContent$",
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": json.dumps({"answer": "her", "confidence": 0.97})}
                                ],
                                "role": "model",
                            }
                        }
                    ],
                },
            )
        )

        result = await adapter.call_structured(
            prompt="What is 2+2?", schema=schema
        )
        assert result["answer"] == "her"
        assert result["confidence"] == 0.97

    @respx.mock
    async def test_no_key_raises(self) -> None:
        s = ProviderSettings(
            provider_name="gemini", api_key="", extra={"gemini_model": "flash"}
        )
        adapter = GeminiLLM(settings=s)
        with pytest.raises(ProviderError, match="no API key"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )


# ── call_structured() — error paths ───────────────────────────────────────────


class TestCallStructuredErrors:

    @respx.mock
    async def test_rate_limit_429_is_retryable(self, adapter: GeminiLLM) -> None:
        respx.post(
            "https://generativelanguage.googleapis.com",
            path__regex=r"^/v1beta/models/.+:generateContent$",
        ).mock(return_value=httpx.Response(429, json={"error": {"message": "quota"}}))

        with pytest.raises(ProviderError, match="rate limited") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is True

    @respx.mock
    async def test_forbidden_403_not_retryable(self, adapter: GeminiLLM) -> None:
        respx.post(
            "https://generativelanguage.googleapis.com",
            path__regex=r"^/v1beta/models/.+:generateContent$",
        ).mock(return_value=httpx.Response(403, json={"error": {"message": "invalid key"}}))

        with pytest.raises(ProviderError, match="403") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is False

    @respx.mock
    async def test_connection_error_is_retryable(self, adapter: GeminiLLM) -> None:
        respx.post(
            "https://generativelanguage.googleapis.com",
            path__regex=r"^/v1beta/models/.+:generateContent$",
        ).mock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(ProviderError, match="connection error") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is True


# ── Helper: _build_gemini_body ────────────────────────────────────────────────


class TestBuildGeminiBody:

    def test_basic_body(self) -> None:
        body = _build_gemini_body(
            prompt="what is sky?",
            schema={"color": {"type": "string"}},
            temperature=0.0,
            max_tokens=256,
        )
        assert body["contents"][0]["role"] == "user"
        assert body["generationConfig"]["temperature"] == 0.0
        assert body["generationConfig"]["maxOutputTokens"] == 256
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert body["generationConfig"]["responseSchema"] == {
            "type": "object",
            "properties": {"color": {"type": "string"}},
        }

    def test_numeric_field_preserved(self) -> None:
        schema = {"score": {"type": "number"}, "count": {"type": "integer"}}
        body = _build_gemini_body("q", schema, 0.0, 256)
        rs = body["generationConfig"]["responseSchema"]
        assert rs["properties"]["score"]["type"] == "number"
        assert rs["properties"]["count"]["type"] == "integer"

    def test_unknown_keys_stripped(self) -> None:
        schema: dict[str, object] = {
            "type": "object",
            "description": "A schema",
            "title": "Answer",
            "properties": {
                "text": {"type": "string", "custom_key": "stripped"}
            },
        }
        body = _build_gemini_body("q", schema, 0.0, 256)
        rs = body["generationConfig"]["responseSchema"]
        assert "description" not in rs
        assert "title" not in rs
        assert rs["properties"]["text"]["type"] == "string"
        assert "custom_key" not in rs["properties"]["text"]
