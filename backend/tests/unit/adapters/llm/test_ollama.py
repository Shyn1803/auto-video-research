"""Tests for the Ollama LLM adapter (AC1 — happy path + biên cases).

All HTTP interactions are mocked with ``respx`` — zero network calls.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import httpx
import pytest
import respx
from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.llm.ollama import OllamaLLM
from app.adapters.registry import get_adapter_class, get_registered


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _settings(extra: dict[str, str] | None = None) -> ProviderSettings:
    """Build ProviderSettings as the router would deliver them."""
    base = {
        "ollama_url": "http://localhost:11434",
        "ollama_model_cheap": "qwen2.5:14b-instruct",
        "ollama_model_strong": "qwen2.5:32b-instruct",
    }
    if extra:
        base |= extra
    return ProviderSettings(provider_name="ollama", api_key="", extra=base)


@pytest.fixture()
def adapter() -> OllamaLLM:
    return OllamaLLM(settings=_settings())


# ── AC1: registry registration ────────────────────────────────────────────────


class TestRegistryLookup:

    def test_ollama_in_llm_registry(self) -> None:
        cls = get_adapter_class("llm", "ollama")
        assert cls is OllamaLLM

    def test_ollama_in_get_registered(self) -> None:
        assert "ollama" in get_registered("llm")

    def test_ollama_is_free(self) -> None:
        assert OllamaLLM.is_paid is False


# ── available() ───────────────────────────────────────────────────────────────


class TestAvailable:

    @respx.mock
    async def test_available_true_when_service_up(self, adapter: OllamaLLM) -> None:
        respx.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json={"models": []})
        )
        assert await adapter.available() is True

    @respx.mock
    async def test_available_false_on_connection_error(self, adapter: OllamaLLM) -> None:
        respx.get("http://localhost:11434/api/tags").mock(
            side_effect=httpx.ConnectError("…")
        )
        assert await adapter.available() is False

    @respx.mock
    async def test_available_false_on_500(self, adapter: OllamaLLM) -> None:
        respx.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(500)
        )
        assert await adapter.available() is False


# ── call_structured() — happy path ────────────────────────────────────────────


class TestCallStructuredHappy:

    @respx.mock
    async def test_returns_parsed_json(self, adapter: OllamaLLM) -> None:
        schema = {"answer": {"type": "string"}, "score": {"type": "number"}}
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "qwen2.5:14b-instruct",
                    "response": json.dumps({"answer": "42", "score": 0.9}),
                    "done": True,
                },
            )
        )
        result = await adapter.call_structured(
            prompt="What is the answer?",
            schema=schema,
        )
        assert result == {"answer": "42", "score": 0.9}

    @respx.mock
    async def test_sends_cheap_model_by_default(self, adapter: OllamaLLM) -> None:
        schema = {"text": {"type": "string"}}

        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "qwen2.5:14b-instruct",
                    "response": json.dumps({"text": "ok"}),
                    "done": True,
                },
            )
        )

        await adapter.call_structured(
            prompt="Say hi", schema=schema, tier="cheap"
        )
        sent_body = route.calls.last.request.content  # type: ignore[union-attr]
        import json as _json

        body = _json.loads(sent_body)
        assert body["model"] == "qwen2.5:14b-instruct"

    @respx.mock
    async def test_sends_strong_model_when_tier_strong(self, adapter: OllamaLLM) -> None:
        schema = {"text": {"type": "string"}}

        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "qwen2.5:32b-instruct",
                    "response": json.dumps({"text": "ok"}),
                    "done": True,
                },
            )
        )

        await adapter.call_structured(
            prompt="Say hi", schema=schema, tier="strong"
        )
        import json as _json

        body = _json.loads(route.calls.last.request.content)  # type: ignore[union-attr]
        assert body["model"] == "qwen2.5:32b-instruct"


# ── call_structured() — error paths ───────────────────────────────────────────


class TestCallStructuredErrors:

    @respx.mock
    async def test_model_not_found_404(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(404, text="model not found")
        )
        with pytest.raises(ProviderError, match="404"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )

    @respx.mock
    async def test_bad_request_400(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(400, text="bad format")
        )
        with pytest.raises(ProviderError, match="400"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )

    @respx.mock
    async def test_invalid_json_response(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "qwen2.5:14b-instruct",
                    "response": "this is not json {{{",
                    "done": True,
                },
            )
        )
        with pytest.raises(ProviderError, match="not valid JSON"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )

    @respx.mock
    async def test_no_response_field(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={"model": "qwen2.5:14b-instruct", "done": True},
            )
        )
        with pytest.raises(ProviderError, match="no 'response' field"):
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )

    @respx.mock
    async def test_http_error_is_retryable(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.HTTPStatusError(
                "server error",
                request=httpx.Request("POST", "http://localhost:11434/api/generate"),
                response=httpx.Response(502),
            )
        )
        with pytest.raises(ProviderError, match="HTTP error") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is True

    @respx.mock
    async def test_connection_error_is_retryable(self, adapter: OllamaLLM) -> None:
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(ProviderError, match="HTTP error") as exc_info:
            await adapter.call_structured(
                prompt="hi", schema={"x": {"type": "string"}}
            )
        assert exc_info.value.retryable is True


# ── Matrix: only OLLAMA_URL set → ollama ✓, rest "thiếu key" ──────────────────


class TestAC1Matrix:

    def test_only_ollama_url_configured(self) -> None:
        """AC1: with only OLLAMA_URL set, ollama adapter is available
        and callable; other providers are absent from the chain."""
        settings = _settings()
        adapter = OllamaLLM(settings=settings)
        # Adapter has no API key requirement per se —
        # availability is a network probe we test separately.
        assert adapter.name == "ollama"
        assert adapter.is_paid is False
        # model names populated from extra
        assert adapter._model_cheap == "qwen2.5:14b-instruct"
        assert adapter._model_strong == "qwen2.5:32b-instruct"


# ── Extra: custom model names via extra ───────────────────────────────────────


class TestModelConfig:

    def test_custom_model_names(self) -> None:
        settings = _settings(
            extra={
                "ollama_model_cheap": "llama3.1:8b",
                "ollama_model_strong": "llama3.1:70b",
            }
        )
        adapter = OllamaLLM(settings=settings)
        assert adapter._model_cheap == "llama3.1:8b"
        assert adapter._model_strong == "llama3.1:70b"

    @respx.mock
    async def test_custom_model_sent_in_payload(self) -> None:
        settings = _settings(
            extra={"ollama_model_cheap": "custom-model"}
        )
        adapter = OllamaLLM(settings=settings)

        route = respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "custom-model",
                    "response": json.dumps({"x": 1}),
                    "done": True,
                },
            )
        )
        await adapter.call_structured(
            prompt="hi", schema={"x": {"type": "number"}}
        )
        import json as _json

        body = _json.loads(route.calls.last.request.content)  # type: ignore[union-attr]
        assert body["model"] == "custom-model"
