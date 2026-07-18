"""MinIO / S3-compatible storage adapter (Task 5-3).

Minimal implementation sufficient for the Asset Worker to store downloaded
stock images and user uploads under a content-addressed key
(``assets/{hash}.{ext}`` per docs/specs/database-schema.md §2.5).

KNOWN GAP (flagged, not silently skipped -- rules/error-handling.md): this
uses a plain authenticated PUT rather than full AWS SigV4 request signing.
It works against a MinIO instance configured for path-style access with a
static access/secret pair passed as basic auth, which is sufficient for the
local-first dev/self-hosted deployment this project targets (docs/CONFIGURATION.md
MINIO_* defaults), but a hardened multi-tenant/cloud-S3 deployment should
replace this with a signing library (e.g. ``boto3``) -- tracked as a
follow-up for task 9-3 (voice/asset worker hardening), not done here to
keep 5-3 scoped.
"""

from __future__ import annotations

import logging

import httpx

from app.adapters.base import ProviderError, ProviderSettings, StorageAdapter
from app.adapters.registry import register_storage

logger = logging.getLogger("avr.storage.minio")


@register_storage("minio")
class MinioStorage(StorageAdapter):
    """MinIO object storage -- free, self-hosted, no ALLOW_PAID gate."""

    name: str = "minio"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._base_url = (self.settings.extra.get("minio_url") or "").rstrip("/")
        self._access_key = self.settings.extra.get("minio_access_key", "")
        self._secret_key = self.settings.extra.get("minio_secret_key", "")
        self._bucket = self.settings.extra.get("bucket") or "avr-uploads"

    async def available(self) -> bool:
        return bool(self._base_url)

    def _object_url(self, key: str) -> str:
        return f"{self._base_url}/{self._bucket}/{key.lstrip('/')}"

    async def upload(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not self._base_url:
            raise ProviderError("minio: no MINIO_URL configured", retryable=False)

        url = self._object_url(key)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    url,
                    content=data,
                    headers={"Content-Type": content_type},
                    auth=(self._access_key, self._secret_key)
                    if self._access_key
                    else None,
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(
                f"minio upload HTTP {status}: {exc}", retryable=status >= 500
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ProviderError(f"minio connection error: {exc}", retryable=True) from exc

        return url

    async def presign_get(
        self,
        key: str,
        *,
        expires_seconds: int = 3600,
    ) -> str:
        # Simplified: public read bucket -- no query-string signature.
        # See module docstring's KNOWN GAP note.
        return self._object_url(key)
