"""Task 4-3 Step 2 -- arXiv connector."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError
from app.adapters.search.arxiv import ArxivSearch, parse_arxiv_feed

_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>A New Language Model Architecture</title>
    <summary>We propose a new architecture that improves benchmark scores.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00002v1</id>
    <title>Scaling Laws Revisited</title>
    <summary>An empirical study of scaling laws.</summary>
    <published>2024-01-02T00:00:00Z</published>
    <author><name>John Smith</name></author>
  </entry>
</feed>
"""


def test_parse_arxiv_feed_extracts_two_entries():
    results = parse_arxiv_feed(_FEED)
    assert len(results) == 2
    assert results[0]["title"] == "A New Language Model Architecture"
    assert results[0]["url"] == "http://arxiv.org/abs/2401.00001v1"
    assert "propose" in results[0]["snippet"]
    assert results[0]["author"] == "Jane Doe"


@pytest.mark.asyncio
@respx.mock
async def test_search_returns_parsed_results():
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=Response(200, text=_FEED)
    )
    adapter = ArxivSearch()
    results = await adapter.search("language model", max_results=5)
    assert len(results) == 2


@pytest.mark.asyncio
@respx.mock
async def test_5xx_raises_retryable_provider_error():
    respx.get("http://export.arxiv.org/api/query").mock(return_value=Response(503))
    adapter = ArxivSearch()
    with pytest.raises(ProviderError) as exc_info:
        await adapter.search("x")
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_available_always_true_free_no_key():
    assert await ArxivSearch().available() is True
