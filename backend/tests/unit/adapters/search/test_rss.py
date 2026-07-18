"""Task 4-3 Step 2 -- RSS connector."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError, ProviderSettings
from app.adapters.search.rss import RssSearch, parse_rss_feed

_FEED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Example AI Blog</title>
  <item>
    <title>Announcing GPT-Next</title>
    <link>https://example.com/gpt-next</link>
    <description>A new model with better reasoning.</description>
    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
    <author>team@example.com</author>
  </item>
  <item>
    <title>Unrelated cooking post</title>
    <link>https://example.com/cooking</link>
    <description>How to bake bread.</description>
    <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
  </item>
</channel>
</rss>
"""


def test_parse_rss_feed_filters_by_query():
    matches = parse_rss_feed(_FEED_XML, "gpt")
    assert len(matches) == 1
    assert matches[0]["title"] == "Announcing GPT-Next"


def test_parse_rss_feed_empty_query_returns_all():
    matches = parse_rss_feed(_FEED_XML, "")
    assert len(matches) == 2


@pytest.mark.asyncio
@respx.mock
async def test_search_uses_configured_feed_list():
    respx.get("https://feed.example.com/rss.xml").mock(
        return_value=Response(200, content=_FEED_XML)
    )
    adapter = RssSearch(
        ProviderSettings(extra={"rss_feeds": "https://feed.example.com/rss.xml"})
    )
    results = await adapter.search("gpt", max_results=10)
    assert len(results) == 1


@pytest.mark.asyncio
@respx.mock
async def test_all_feeds_unreachable_raises_retryable_error():
    import httpx

    respx.get("https://feed.example.com/rss.xml").mock(
        side_effect=httpx.ConnectError("dns fail")
    )
    adapter = RssSearch(
        ProviderSettings(extra={"rss_feeds": "https://feed.example.com/rss.xml"})
    )
    with pytest.raises(ProviderError) as exc_info:
        await adapter.search("gpt")
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
@respx.mock
async def test_one_bad_feed_does_not_sink_others():
    respx.get("https://good.example.com/rss.xml").mock(
        return_value=Response(200, content=_FEED_XML)
    )
    respx.get("https://bad.example.com/rss.xml").mock(return_value=Response(500))
    adapter = RssSearch(
        ProviderSettings(
            extra={
                "rss_feeds": "https://good.example.com/rss.xml,https://bad.example.com/rss.xml"
            }
        )
    )
    results = await adapter.search("gpt")
    assert len(results) == 1
