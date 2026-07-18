"""Task 4-3 Step 2 -- HN Algolia connector."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError
from app.adapters.search.hn_algolia import HackerNewsAlgoliaSearch, parse_hn_response

_RESPONSE = {
    "hits": [
        {
            "title": "New AI model beats benchmark",
            "url": "https://example.com/article",
            "story_text": None,
            "author": "someuser",
            "created_at": "2024-01-01T00:00:00.000Z",
            "objectID": "12345",
        },
        {
            "title": None,
            "story_title": "Ask HN: something",
            "url": None,
            "story_text": "text body",
            "author": "otheruser",
            "created_at": "2024-01-02T00:00:00.000Z",
            "objectID": "67890",
        },
    ]
}


def test_parse_hn_response_two_hits():
    results = parse_hn_response(_RESPONSE)
    assert len(results) == 2
    assert results[0]["title"] == "New AI model beats benchmark"
    assert results[0]["url"] == "https://example.com/article"
    assert results[1]["title"] == "Ask HN: something"
    assert results[1]["url"] == "https://news.ycombinator.com/item?id=67890"


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_parsed_results():
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=Response(200, json=_RESPONSE)
    )
    adapter = HackerNewsAlgoliaSearch()
    results = await adapter.search("ai model", max_results=5)
    assert len(results) == 2


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_retryable_provider_error():
    import httpx

    respx.get("https://hn.algolia.com/api/v1/search").mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )
    adapter = HackerNewsAlgoliaSearch()
    with pytest.raises(ProviderError) as exc_info:
        await adapter.search("x")
    assert exc_info.value.retryable is True
