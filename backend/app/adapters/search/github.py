"""GitHub repository search connector (Task 4-3 Step 2).

Works unauthenticated (free, low rate limit) or with a token via
ProviderSettings.api_key (GITHUB_TOKEN) for a higher rate limit -- both are
"free" (is_paid=False), a token just raises the ceiling, per SRS FR-21's
"0 API keys" baseline.
"""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search

logger = logging.getLogger("avr.search.github")

_API_URL = "https://api.github.com/search/repositories"


@register_search("github")
class GitHubSearch(SearchAdapter):
    """GitHub repo search -- free with or without a token."""

    name: str = "github"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._token = self.settings.api_key

    async def available(self) -> bool:
        return True  # works unauthenticated too

    async def search(
        self, query: str, *, max_results: int = 10, language: str = "vi"
    ) -> list[dict[str, str]]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    _API_URL,
                    params={"q": query, "per_page": max_results, "sort": "updated"},
                    headers=headers,
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 403:
                raise ProviderError(
                    f"github rate limited (403): {exc}", retryable=True
                ) from exc
            raise ProviderError(
                f"github HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"github connection error: {exc}", retryable=True) from exc

        return parse_github_response(resp.json())


def parse_github_response(raw: dict) -> list[dict[str, str]]:
    """Parse the GitHub search-repositories JSON body (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for item in raw.get("items", []):
        owner = (item.get("owner") or {}).get("login", "")
        results.append(
            {
                "title": item.get("full_name") or "",
                "url": item.get("html_url") or "",
                "snippet": item.get("description") or "",
                "published_at": item.get("updated_at") or "",
                "author": owner,
            }
        )
    return results
