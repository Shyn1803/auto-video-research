"""Unsplash stock-photo adapter (Task 5-3). Free, key-gated (Access Key)."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import AssetStockAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_asset_stock

logger = logging.getLogger("avr.assetstock.unsplash")

_SEARCH_URL = "https://api.unsplash.com/search/photos"


@register_asset_stock("unsplash")
class UnsplashAssetStock(AssetStockAdapter):
    """Unsplash API search -- free, key-gated."""

    name: str = "unsplash"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._access_key = self.settings.extra.get("unsplash_access_key", "")

    async def available(self) -> bool:
        return bool(self._access_key)

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        license_: str = "free",
    ) -> list[dict[str, str]]:
        if not self._access_key:
            raise ProviderError(
                "unsplash: no UNSPLASH_ACCESS_KEY configured", retryable=False
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    _SEARCH_URL,
                    headers={"Authorization": f"Client-ID {self._access_key}"},
                    params={"query": query, "per_page": max_results},
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"unsplash HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"unsplash connection error: {exc}", retryable=True) from exc

        return parse_unsplash_response(resp.json())[:max_results]


def parse_unsplash_response(raw: dict) -> list[dict[str, str]]:
    """Parse an Unsplash JSON search response (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for photo in raw.get("results", []):
        urls = photo.get("urls", {})
        user = photo.get("user", {})
        results.append(
            {
                "provider": "unsplash",
                "url": urls.get("regular") or urls.get("full") or "",
                "thumb_url": urls.get("small") or urls.get("thumb") or "",
                "attribution": user.get("name") or "",
                "attribution_url": (user.get("links") or {}).get("html") or "",
                "license": "Unsplash License",
                "width": str(photo.get("width") or ""),
                "height": str(photo.get("height") or ""),
            }
        )
    return results
