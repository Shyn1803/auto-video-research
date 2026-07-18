"""Unit tests for AssetService (Task 5-3, FR-20).

Mocks all HTTP with respx per rules/testing.md — no live network calls.
Exercises the AC list from .claude/tasks/5-3-assetpicker.md:
  AC1 (happy): search -> select -> asset has license record
  AC2 (BR-2):  duplicate upload reuses the existing asset
  AC3 (BR-3):  0 key -> stock_status().active is False
  AC5 (BR-4):  stock selection downloads server-side, never trusts a
               non-allowlisted host (SSRF defense-in-depth)
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from app.core.config import Settings
from app.core.router import ProviderRouter
from app.services.asset_service import (
    AssetFetchError,
    AssetService,
    AssetStockUnavailable,
    AssetValidationError,
)

# Adapters must be registered before the router can resolve them.
import app.adapters.assetstock  # noqa: F401,E402
import app.adapters.storage  # noqa: F401,E402


class _FakeSession:
    """Minimal AsyncSession stand-in: content_hash lookups + add/flush/commit."""

    def __init__(self, existing_by_hash: dict[str, object] | None = None):
        self._by_hash = existing_by_hash or {}
        self.added: list[object] = []
        self.flush = AsyncMock()
        self.commit = AsyncMock()

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, stmt):
        # Extract the bound content_hash literal from the compiled query.
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        result = MagicMock()
        found = None
        for h, asset in self._by_hash.items():
            if h in str(compiled):
                found = asset
                break
        result.scalar_one_or_none.return_value = found
        return result


def _settings(**overrides) -> Settings:
    base = {
        "allow_paid": False,
        "storage_provider": "minio",
        "minio_url": "http://minio.test:9000",
        "minio_access_key": "ak",
        "minio_secret_key": "sk",
        "s3_bucket": "avr-uploads",
    }
    base.update(overrides)
    return Settings(**base)


# ── AC3 / BR-3: 0 key -> stock tab disabled ────────────────────────────────


@pytest.mark.asyncio
async def test_stock_status_inactive_when_no_key():
    settings = _settings(asset_chain="pexels,pixabay,unsplash")
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    status = await svc.stock_status()
    assert status["active"] is False
    assert status["providers"] == []


@pytest.mark.asyncio
async def test_stock_status_active_when_key_present():
    settings = _settings(asset_chain="pexels", pexels_api_key="test-key")
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    status = await svc.stock_status()
    assert status["active"] is True
    assert "pexels" in status["providers"]


# ── AC1 (happy path): search returns license + source per result (BR-1) ───


@pytest.mark.asyncio
@respx.mock
async def test_search_stock_returns_license_and_source():
    settings = _settings(asset_chain="pexels", pexels_api_key="test-key")
    respx.get("https://api.pexels.com/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "src": {"large2x": "https://images.pexels.com/photos/1/gpu.jpg"},
                        "photographer": "Jane Doe",
                        "photographer_url": "https://pexels.com/@jane",
                        "width": 1920,
                        "height": 1080,
                    }
                ]
            },
        )
    )
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    results = await svc.search("GPU datacenter")
    assert len(results) == 1
    assert results[0]["license"] == "Pexels License"
    assert results[0]["provider"] == "pexels"
    assert results[0]["url"].startswith("https://images.pexels.com/")


@pytest.mark.asyncio
async def test_search_stock_unavailable_raises_when_no_provider():
    settings = _settings(asset_chain="pexels")  # no key
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    with pytest.raises(AssetStockUnavailable):
        await svc.search("anything")


# ── AC2 / BR-2: duplicate upload reuses, no new record ─────────────────────


@pytest.mark.asyncio
async def test_upload_dedupes_by_hash():
    data = b"fake-jpeg-bytes"
    content_hash = hashlib.sha256(data).hexdigest()
    existing_asset = MagicMock()
    session = _FakeSession({content_hash: existing_asset})
    settings = _settings()
    svc = AssetService(session, router=ProviderRouter(settings), settings=settings)

    asset, reused = await svc.upload(
        data=data, content_type="image/jpeg", uploaded_by="u1"
    )

    assert reused is True
    assert asset is existing_asset
    assert session.added == []  # BR-2: no new record created


@pytest.mark.asyncio
async def test_upload_rejects_wrong_type():
    settings = _settings()
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    with pytest.raises(AssetValidationError):
        await svc.upload(data=b"abc", content_type="image/gif", uploaded_by="u1")


@pytest.mark.asyncio
async def test_upload_rejects_oversize():
    settings = _settings()
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    oversize = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(AssetValidationError):
        await svc.upload(data=oversize, content_type="image/png", uploaded_by="u1")


@pytest.mark.asyncio
@respx.mock
async def test_upload_new_file_stores_and_creates_asset():
    data = b"fake-png-bytes"
    settings = _settings()
    respx.put(
        "http://minio.test:9000/avr-uploads/assets/"
        + hashlib.sha256(data).hexdigest()
        + ".png"
    ).mock(return_value=httpx.Response(200))
    session = _FakeSession()
    svc = AssetService(session, router=ProviderRouter(settings), settings=settings)

    asset, reused = await svc.upload(data=data, content_type="image/png", uploaded_by="u1")

    assert reused is False
    assert asset.license == "user_upload"
    assert asset.provider == "user_upload"
    assert session.added == [asset]


# ── AC5 / BR-4: stock selection downloads server-side into MinIO ──────────


@pytest.mark.asyncio
@respx.mock
async def test_fetch_stock_downloads_and_stores(monkeypatch):
    url = "https://images.pexels.com/photos/1/gpu.jpg"
    data = b"downloaded-image-bytes"
    respx.get(url).mock(
        return_value=httpx.Response(200, content=data, headers={"content-type": "image/jpeg"})
    )
    content_hash = hashlib.sha256(data).hexdigest()
    respx.put(f"http://minio.test:9000/avr-uploads/assets/{content_hash}.jpg").mock(
        return_value=httpx.Response(200)
    )
    settings = _settings()
    session = _FakeSession()
    svc = AssetService(session, router=ProviderRouter(settings), settings=settings)

    asset = await svc.fetch_stock(
        url=url, provider="pexels", license_="Pexels License", attribution="Jane Doe"
    )

    assert asset.license == "Pexels License"
    assert asset.source_url == url
    assert asset.provider == "pexels"
    assert session.added == [asset]


@pytest.mark.asyncio
async def test_fetch_stock_rejects_non_allowlisted_host():
    """SSRF defense-in-depth: even a client-supplied 'stock' URL must be on
    the allowlist -- render/preview never fetches arbitrary external URLs
    (rules/security.md)."""
    settings = _settings()
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    with pytest.raises(AssetFetchError):
        await svc.fetch_stock(
            url="https://evil.example.com/payload.jpg",
            provider="pexels",
            license_="Pexels License",
        )


@pytest.mark.asyncio
async def test_fetch_stock_rejects_missing_license():
    settings = _settings()
    svc = AssetService(_FakeSession(), router=ProviderRouter(settings), settings=settings)
    with pytest.raises(AssetValidationError):
        await svc.fetch_stock(
            url="https://images.pexels.com/photos/1/gpu.jpg",
            provider="pexels",
            license_="",
        )
