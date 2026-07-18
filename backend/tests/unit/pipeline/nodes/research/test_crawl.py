"""Task 4-3 Step 3 -- trafilatura crawl + robots.txt + paywall detection."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.adapters.base import ProviderError
from app.pipeline.nodes.research.crawl import (
    check_robots_allowed,
    crawl_url,
    extract_content,
)

_FULL_ARTICLE_HTML = """
<html><head><title>New Model Announced</title></head>
<body>
<article>
<h1>New Model Announced</h1>
<p>Researchers today announced a new AI model that achieves state of the art
results on several benchmarks. The model was trained on a large diverse
dataset and shows significant improvements in reasoning tasks compared to
its predecessor. Independent evaluators confirmed the reported numbers
across multiple test suites, noting consistent gains in accuracy, latency,
and robustness to adversarial prompts. The team plans to open source the
weights next month alongside a detailed technical report describing the
training methodology, data curation pipeline, and evaluation protocol used
throughout the project.</p>
</article>
</body></html>
"""

_PAYWALL_HTML = """
<html><head><title>Premium Article</title></head>
<body>
<article>
<h1>Premium Article</h1>
<p>Subscribe to read more.</p>
</article>
</body></html>
"""


def test_check_robots_allowed_default_allow_when_no_disallow():
    robots_txt = "User-agent: *\nAllow: /"
    assert check_robots_allowed(robots_txt, "https://example.com/article") is True


def test_check_robots_disallow_blocks():
    robots_txt = "User-agent: *\nDisallow: /paywalled/"
    assert check_robots_allowed(robots_txt, "https://example.com/paywalled/x") is False


def test_extract_content_full_article_not_partial():
    title, content, is_partial = extract_content(_FULL_ARTICLE_HTML, "https://example.com/a")
    assert title == "New Model Announced"
    assert content is not None
    assert is_partial is False


def test_extract_content_short_page_is_partial():
    title, content, is_partial = extract_content(_PAYWALL_HTML, "https://example.com/paywalled")
    assert title == "Premium Article"
    assert is_partial is True


@pytest.mark.asyncio
@respx.mock
async def test_crawl_url_happy_path():
    respx.get("https://example.com/robots.txt").mock(
        return_value=Response(200, text="User-agent: *\nAllow: /")
    )
    respx.get("https://example.com/article").mock(
        return_value=Response(200, text=_FULL_ARTICLE_HTML)
    )
    result = await crawl_url("https://example.com/article")
    assert result.allowed_by_robots is True
    assert result.partial_content is False
    assert result.title == "New Model Announced"


@pytest.mark.asyncio
@respx.mock
async def test_crawl_url_paywall_marks_partial():
    respx.get("https://example.com/robots.txt").mock(return_value=Response(404))
    respx.get("https://example.com/paywalled").mock(
        return_value=Response(200, text=_PAYWALL_HTML)
    )
    result = await crawl_url("https://example.com/paywalled")
    assert result.partial_content is True
    assert result.title == "Premium Article"


@pytest.mark.asyncio
@respx.mock
async def test_crawl_url_respects_robots_disallow():
    respx.get("https://example.com/robots.txt").mock(
        return_value=Response(200, text="User-agent: *\nDisallow: /blocked/")
    )
    result = await crawl_url("https://example.com/blocked/page")
    assert result.allowed_by_robots is False
    assert result.content is None


@pytest.mark.asyncio
@respx.mock
async def test_crawl_url_5xx_raises_retryable():
    respx.get("https://example.com/robots.txt").mock(return_value=Response(404))
    respx.get("https://example.com/down").mock(return_value=Response(503))
    with pytest.raises(ProviderError) as exc_info:
        await crawl_url("https://example.com/down")
    assert exc_info.value.retryable is True
