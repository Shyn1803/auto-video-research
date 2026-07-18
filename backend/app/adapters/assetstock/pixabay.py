"""Pixabay stock-photo adapter (Task 5-3). Free, key-gated."""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import AssetStockAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_asset_stock

logger = logging.getLogger("avr.assetstock.pixabay")

_SEARCH_URL = "https://pixabay.com/api/"


@register_asset_stock("pixabay")
class PixabayAssetStock(AssetStockAdapter):
    """Pixabay API search -- free, key-gated."""

    name: str = "pixabay"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._api_key = self.settings.extra.get("pixabay_api_key", "")

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
            raise ProviderError("pixabay: no PIXABAY_API_KEY configured", retryable=False)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    _SEARCH_URL,
                    params={"key": self._api_key, "q": query, "per_page": max(max_results, 3)},
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"pixabay HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"pixabay connection error: {exc}", retryable=True) from exc

        return parse_pixabay_response(resp.json())[:max_results]


def parse_pixabay_response(raw: dict) -> list[dict[str, str]]:
    """Parse a Pixabay JSON search response (testable without HTTP)."""
    results: list[dict[str, str]] = []
    for hit in raw.get("hits", []):
        results.append(
            {
                "provider": "pixabay",
                "url": hit.get("largeImageURL") or hit.get("webformatURL") or "",
                "thumb_url": hit.get("previewURL") or "",
                "attribution": hit.get("user") or "",
                "attribution_url": "",
                "license": "Pixabay License",
                "width": str(hit.get("imageWidth") or ""),
                "height": str(hit.get("imageHeight") or ""),
            }
        )
    return results
