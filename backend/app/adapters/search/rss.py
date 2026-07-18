"""RSS-list connector -- trusted blog feeds, config-driven (Task 4-3 Step 2).

Unlike the other connectors, RSS feeds have no server-side search endpoint:
this fetches each configured feed and filters entries by a simple
title/summary substring match against *query*. The seed feed list ("Decisions
already locked": OpenAI/Anthropic/Google/DeepMind/NVIDIA/HuggingFace) lives
here as a default and is overridable via ``ProviderSettings.extra["rss_feeds"]``
(comma-separated URLs) so ops can add a feed without a code change, per
rules/configuration-env.md.
"""

from __future__ import annotations

import logging

import feedparser
import httpx

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search

logger = logging.getLogger("avr.search.rss")

DEFAULT_FEEDS: list[str] = [
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://deepmind.google/blog/rss.xml",
    "https://blogs.nvidia.com/feed/",
    "https://huggingface.co/blog/feed.xml",
]

# All entries considered "trusted" per the RSS list decision (docs/specs/
# prompts.md-adjacent domain rule: these 6 official vendor blogs are the
# curated trusted-domain set for this connector).
TRUSTED = True


@register_search("rss")
class RssSearch(SearchAdapter):
    """Trusted vendor-blog RSS feeds, filtered client-side by *query*."""

    name: str = "rss"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        feeds_csv = self.settings.extra.get("rss_feeds", "")
        self._feeds = [f.strip() for f in feeds_csv.split(",") if f.strip()] or DEFAULT_FEEDS

    async def available(self) -> bool:
        return True

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "vi"
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        query_lower = query.lower()
        failures = 0

        async with httpx.AsyncClient(timeout=20.0) as client:
            for feed_url in self._feeds:
                try:
                    resp = await client.get(feed_url)
                    resp.raise_for_status()
                except (httpx.HTTPError, OSError) as exc:
                    # One bad feed shouldn't sink the whole connector (BR-1
                    # applies at the node-orchestration level to connectors
                    # as a whole; here it's the same "isolate the failure"
                    # principle one level down, per feed).
                    logger.warning("rss feed unreachable %s: %s", feed_url, exc)
                    failures += 1
                    continue
                results.extend(parse_rss_feed(resp.content, query_lower))

        if self._feeds and failures == len(self._feeds):
            raise ProviderError(
                f"rss: all {len(self._feeds)} configured feeds unreachable",
                retryable=True,
            )

        return results[:max_results]


def parse_rss_feed(raw_bytes: bytes, query_lower: str) -> list[dict[str, str]]:
    """Parse one feed's bytes and filter entries matching *query_lower*
    (testable without HTTP)."""
    parsed = feedparser.parse(raw_bytes)
    matches: list[dict[str, str]] = []
    for entry in parsed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        haystack = f"{title} {summary}".lower()
        if query_lower and query_lower not in haystack:
            continue
        matches.append(
            {
                "title": title,
                "url": entry.get("link", ""),
                "snippet": summary,
                "published_at": entry.get("published", ""),
                "author": entry.get("author", ""),
            }
        )
    return matches
