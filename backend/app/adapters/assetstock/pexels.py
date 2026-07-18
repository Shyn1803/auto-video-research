"""Pexels stock-photo adapter (Task 5-3).

Free tier requires an API key (``PEXELS_API_KEY``) but has no cost --
``is_paid = False`` per is_paid semantics (cost, not "requires signup").
"""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import AssetStockAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_asset_stock

logger = logging.getLogger("avr.assetstock.pexels")

_SEARCH_URL = "https://api.pexels.com/v1/search"


@register_asset_stock("pexels")
class PexelsAssetStock(AssetStockAdapter):
    """Pexels API search -- free, key-gated."""

    name: str = "pexels"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key = self.settings.extra.get("pexels_api_key", "")

    async def available(self) -> bool:
        return bool(self._api_key)

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        license_: str = "free",
    ) -> list[dict[str, str]]:
        if not self._api_key:
            raise ProviderError("pexels: no PEXELS_API_KEY configured", retryable=False)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    _SEARCH_URL,
                    headers={"Authorization": self._api_key},
                    params={"query": query, "per_page": max_results},
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"pexels HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"pexels connection error: {exc}", retryable=True) from exc

        return parse_pexels_response(resp.json())[:max_results]


def parse_pexels_response(raw: dict) -> list[dict[str, str]]:
    """Parse a Pexels JSON search response (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for photo in raw.get("photos", []):
        src = photo.get("src", {})
        results.append(
            {
                "provider": "pexels",
                "url": src.get("large2x") or src.get("original") or "",
                "thumb_url": src.get("medium") or src.get("small") or "",
                "attribution": photo.get("photographer") or "",
                "attribution_url": photo.get("photographer_url") or "",
                "license": "Pexels License",
                "width": str(photo.get("width") or ""),
                "height": str(photo.get("height") or ""),
            }
        )
    return results
