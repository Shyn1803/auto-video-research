"""Crawl -- trafilatura extraction + robots.txt + paywall detection (Task 4-3 Step 3).

BR-1 applies at the connector-orchestration level; a single URL failing
here (robots disallow, timeout, extraction failure) should be handled by
the *caller* skipping that source, not by this module swallowing errors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from app.adapters.base import ProviderError

logger = logging.getLogger("avr.research.crawl")

USER_AGENT = "AVR-research-bot/1.0 (+https://github.com/avr)"

# Below this many characters of extracted body text, treat the page as
# paywalled/preview-only (title + a short teaser is all that's public) --
# fall back to title+abstract only and flag partial_content (Scope: "paywall
# -> title+abstract + partial_content").
_PAYWALL_MIN_CHARS = 400


@dataclass
class CrawlResult:
    url: str
    title: str | None
    content: str | None
    partial_content: bool
    allowed_by_robots: bool


def check_robots_allowed(robots_txt: str, url: str, *, user_agent: str = USER_AGENT) -> bool:
    """Return True if *user_agent* may fetch *url* per *robots_txt* content.

    Pure/testable -- no I/O. An empty/unparseable robots.txt defaults to
    allow (most sites without a robots.txt intend to allow crawling).
    """
    parser = robotparser.RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return parser.can_fetch(user_agent, url)


def extract_content(html: str, url: str) -> tuple[str | None, str | None, bool]:
    """Extract (title, content, is_partial) from *html* via trafilatura.

    is_partial=True when the extracted body is too short to be the full
    article (paywall/preview heuristic) -- title is still returned so the
    caller can keep a title+abstract-only source per Scope.
    """
    content = trafilatura.extract(html, url=url, favor_recall=True)
    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = metadata.title if metadata else None

    if not content:
        return title, None, True

    is_partial = len(content) < _PAYWALL_MIN_CHARS
    return title, content, is_partial


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


async def crawl_url(url: str, *, respect_robots: bool = True) -> CrawlResult:
    """Fetch *url*, respecting robots.txt, and extract its main content.

    Raises ProviderError(retryable=True) on network failure -- the caller
    (node orchestration, Step 7) is responsible for catching this per-URL
    and recording the failure without aborting the whole research node.
    """
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        allowed = True
        if respect_robots:
            try:
                robots_txt = await _fetch_text(client, robots_url)
                allowed = check_robots_allowed(robots_txt, url)
            except (httpx.HTTPError, OSError):
                # No robots.txt or it's unreachable -- default allow, per
                # check_robots_allowed's own "no file -> allow" convention.
                allowed = True

        if not allowed:
            return CrawlResult(
                url=url, title=None, content=None, partial_content=True, allowed_by_robots=False
            )

        try:
            html = await _fetch_text(client, url)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"crawl {url} HTTP {status}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"crawl {url} connection error: {exc}", retryable=True) from exc

    title, content, is_partial = extract_content(html, url)
    return CrawlResult(
        url=url, title=title, content=content, partial_content=is_partial, allowed_by_robots=True
    )
