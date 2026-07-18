"""Hacker News (Algolia) connector -- free, no key required (Task 4-3 Step 2)."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search

logger = logging.getLogger("avr.search.hn_algolia")

_API_URL = "https://hn.algolia.com/api/v1/search"


@register_search("hn_algolia")
class HackerNewsAlgoliaSearch(SearchAdapter):
    """HN story search via the public Algolia API -- free, no API key."""

    name: str = "hn_algolia"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)

    async def available(self) -> bool:
        return True

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "vi"
    ) -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    _API_URL,
                    params={
                        "query": query,
                        "hitsPerPage": max_results,
                        "tags": "story",
                    },
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"hn_algolia HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"hn_algolia connection error: {exc}", retryable=True) from exc

        return parse_hn_response(resp.json())


def parse_hn_response(raw: dict) -> list[dict[str, str]]:
    """Parse the Algolia HN Search JSON body (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for hit in raw.get("hits", []):
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
        results.append(
            {
                "title": hit.get("title") or hit.get("story_title") or "",
                "url": url,
                "snippet": hit.get("story_text") or "",
                "published_at": hit.get("created_at") or "",
                "author": hit.get("author") or "",
            }
        )
    return results
