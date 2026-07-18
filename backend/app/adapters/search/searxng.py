"""SearXNG meta-search connector -- free, self-hosted (Task 4-3 Step 2).

Base URL comes from ``ProviderSettings.base_url`` (env ``SEARXNG_URL`` per
_ENV_MAP in app/core/config.py) -- never hardcoded.
"""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search

logger = logging.getLogger("avr.search.searxng")


@register_search("searxng")
class SearxngSearch(SearchAdapter):
    """SearXNG instance search -- free, self-hosted, no API key."""

    name: str = "searxng"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._base_url = (self.settings.base_url or "").rstrip("/")

    async def available(self) -> bool:
        return bool(self._base_url)

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "vi"
    ) -> list[dict[str, str]]:
        if not self._base_url:
            raise ProviderError("searxng: no base_url configured (SEARXNG_URL)", retryable=False)

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{self._base_url}/search",
                    params={"q": query, "format": "json", "language": language},
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"searxng HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"searxng connection error: {exc}", retryable=True) from exc

        return parse_searxng_response(resp.json())[:max_results]


def parse_searxng_response(raw: dict) -> list[dict[str, str]]:
    """Parse a SearXNG JSON search response (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for item in raw.get("results", []):
        results.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "snippet": item.get("content") or "",
                "published_at": item.get("publishedDate") or "",
                "author": "",
            }
        )
    return results
