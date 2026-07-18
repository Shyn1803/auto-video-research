"""AssetService — search/upload/fetch-stock for the AssetPicker (Task 5-3, FR-20).

Every asset entering the system gets exactly one ``assets`` row with a
non-empty license before anything else can reference it by ``asset_id``
(rules/security.md). No business logic in the router (rules/code-style.md) —
``app.api.assets`` only translates HTTP <-> this service.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ProviderSettings
from app.adapters.registry import get_adapter_class
from app.core.asset_allowlist import is_allowed_asset_host
from app.core.config import Settings
from app.core.exceptions import AllProvidersFailed
from app.core.router import ProviderRouter
from app.models.asset import Asset

logger = logging.getLogger("avr.services.asset")

ALLOWED_UPLOAD_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB, locked decision (task 5-3 file)


class AssetValidationError(ValueError):
    """Upload rejected: wrong type, too large, or otherwise invalid."""


class AssetStockUnavailable(RuntimeError):
    """No asset_stock provider is currently usable (BR-3)."""


class AssetFetchError(RuntimeError):
    """A stock URL could not be fetched/stored (e.g. SSRF-blocked, download failure)."""


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AssetService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        router: ProviderRouter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.router = router or ProviderRouter(settings)
        self._settings = settings

    # ------------------------------------------------------------------ #
    # BR-3: stock tab gating status (role-agnostic; role message picked FE-side)
    # ------------------------------------------------------------------ #

    async def stock_status(self) -> dict[str, Any]:
        """True key-presence/health check, not just registry+paid-gate.

        ``ProviderRouter.available_providers()`` deliberately does *not*
        call ``adapter.available()`` (that only happens inside ``call()`` /
        ``check_health()`` -- see app/core/router.py docstring + its test
        suite's AC3/AC5). All 3 asset_stock adapters are free (``is_paid =
        False``), so gating on ``available_providers()`` alone would report
        "active" even with zero keys configured -- wrong for BR-3. Checking
        health explicitly here is the correct source for "is the tab usable".
        """
        chain = self.router.get_chain("asset_stock")
        active: list[str] = []
        for name in chain:
            try:
                ok = await self.router.check_health("asset_stock", name)
            except Exception:  # noqa: BLE001 -- treat any check failure as inactive
                ok = False
            if ok:
                active.append(name)
        return {"active": bool(active), "providers": active}

    # ------------------------------------------------------------------ #
    # Search (BR-1: license + source must be present before selection)
    # ------------------------------------------------------------------ #

    async def search(self, query: str, *, max_results: int = 12) -> list[dict[str, str]]:
        if not query or not query.strip():
            return []
        try:
            results: list[dict[str, str]] = await self.router.call(
                "asset_stock",
                "search",
                kwargs={"query": query.strip(), "max_results": max_results},
            )
        except AllProvidersFailed as exc:
            raise AssetStockUnavailable(str(exc)) from exc
        return results

    # ------------------------------------------------------------------ #
    # Upload (BR-2: dedupe by hash; locked decision: 10MB, jpg/png/webp)
    # ------------------------------------------------------------------ #

    async def upload(
        self,
        *,
        data: bytes,
        content_type: str,
        uploaded_by: str | None,
    ) -> tuple[Asset, bool]:
        """Return (asset, reused). ``reused`` True means BR-2 dedupe fired."""

        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise AssetValidationError(
                f"unsupported content type {content_type!r}; allowed: jpg/png/webp"
            )
        if len(data) > MAX_UPLOAD_BYTES:
            raise AssetValidationError(
                f"file too large ({len(data)} bytes); max {MAX_UPLOAD_BYTES} bytes"
            )
        if len(data) == 0:
            raise AssetValidationError("empty file")

        content_hash = _content_hash(data)
        existing = await self._find_by_hash(content_hash)
        if existing is not None:
            return existing, True

        ext = ALLOWED_UPLOAD_TYPES[content_type]
        key = f"assets/{content_hash}.{ext}"
        storage_path = await self._store(key, data, content_type)

        asset = Asset(
            id=uuid.uuid4(),
            provider="user_upload",
            source_url=None,
            license="user_upload",
            attribution_required=False,
            attribution_text=None,
            media_type="image",
            content_hash=content_hash,
            storage_path=storage_path,
            uploaded_by=uploaded_by,
        )
        self.db.add(asset)
        await self.db.flush()
        return asset, False

    # ------------------------------------------------------------------ #
    # Fetch stock result -> Asset Worker download -> MinIO -> Asset row (BR-4)
    # ------------------------------------------------------------------ #

    async def fetch_stock(
        self,
        *,
        url: str,
        provider: str,
        license_: str,
        attribution: str = "",
        attribution_required: bool = True,
    ) -> Asset:
        """Download a stock result server-side and register it as an internal
        asset (BR-4): the render/preview path never fetches an external URL
        (glossary rule 4 / rules/security.md) -- only this one-time server
        download does, and only for an allowlisted CDN host."""

        if not license_:
            raise AssetValidationError("license is required (FR-20)")
        if not is_allowed_asset_host(url):
            # Defense-in-depth: even though results come from our own adapters,
            # never trust a client-supplied URL without re-checking the host.
            raise AssetFetchError(f"url host not allowlisted for stock fetch: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            raise AssetFetchError(f"failed to download stock asset: {exc}") from exc

        data = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        ext = ALLOWED_UPLOAD_TYPES.get(content_type, "jpg")
        content_hash = _content_hash(data)

        existing = await self._find_by_hash(content_hash)
        if existing is not None:
            return existing

        key = f"assets/{content_hash}.{ext}"
        storage_path = await self._store(key, data, content_type)

        asset = Asset(
            id=uuid.uuid4(),
            provider=provider,
            source_url=url,
            license=license_,
            attribution_required=attribution_required,
            attribution_text=attribution or None,
            media_type="image",
            content_hash=content_hash,
            storage_path=storage_path,
            uploaded_by=None,
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    async def _find_by_hash(self, content_hash: str) -> Asset | None:
        result = await self.db.execute(
            select(Asset).where(Asset.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def _store(self, key: str, data: bytes, content_type: str) -> str:
        from app.core.config import get_settings

        settings = self._settings or get_settings()
        cls = get_adapter_class("storage", settings.storage_provider)
        if cls is None:
            raise AssetFetchError(
                f"storage provider not registered: {settings.storage_provider!r}"
            )
        adapter = cls(
            ProviderSettings(
                provider_name=settings.storage_provider,
                extra={
                    "minio_url": settings.minio_url,
                    "minio_access_key": settings.minio_access_key,
                    "minio_secret_key": settings.minio_secret_key,
                    "bucket": settings.s3_bucket,
                },
            )
        )
        return await adapter.upload(key, data, content_type=content_type)
