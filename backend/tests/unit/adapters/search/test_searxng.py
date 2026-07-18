"""Task 4-3 Step 2 -- SearXNG connector."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.search.searxng import SearxngSearch, parse_searxng_response

_RESPONSE = {
    "results": [
        {
            "title": "Vietnamese AI news",
            "url": "https://example.com/vi-ai",
            "content": "Tin tuc AI moi nhat",
            "publishedDate": "2024-01-01",
        }
    ]
}


def test_parse_searxng_response():
    results = parse_searxng_response(_RESPONSE)
    assert len(results) == 1
    assert results[0]["title"] == "Vietnamese AI news"


@pytest.mark.asyncio
async def test_unavailable_without_base_url():
    adapter = SearxngSearch(ProviderSettings(base_url=""))
    assert await adapter.available() is False
    with pytest.raises(ProviderError):
        await adapter.search("x")


@pytest.mark.asyncio
@respx.mock
async def test_search_with_configured_base_url():
    respx.get("http://searxng.local/search").mock(
        return_value=Response(200, json=_RESPONSE)
    )
    adapter = SearxngSearch(ProviderSettings(base_url="http://searxng.local"))
    assert await adapter.available() is True
    results = await adapter.search("ai", max_results=5)
    assert len(results) == 1


@pytest.mark.asyncio
@respx.mock
async def test_5xx_is_retryable():
    respx.get("http://searxng.local/search").mock(return_value=Response(500))
    adapter = SearxngSearch(ProviderSettings(base_url="http://searxng.local"))
    with pytest.raises(ProviderError) as exc_info:
        await adapter.search("x")
    assert exc_info.value.retryable is True
