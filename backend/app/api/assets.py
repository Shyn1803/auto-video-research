"""Asset endpoints — search stock / upload / fetch-stock (Task 5-3, FR-20, §6 api-spec).

Contract change (new endpoints, docs/specs/api-spec.md §6 updated in the same PR):
  GET  /api/assets/stock-status         BR-3 gating info (any authenticated role)
  GET  /api/assets/search?q=            BR-1: proxies the asset_stock chain via adapter
  POST /api/assets/upload               BR-2: validate + dedupe by hash
  POST /api/assets/fetch-stock          BR-4: server-side download -> MinIO -> asset_id

No business logic here — every route delegates to AssetService
(rules/code-style.md: no business logic in routers). Asset-stock adapter
modules imported eagerly so the registry is populated (see
app/adapters/assetstock/__init__.py and app/adapters/storage/__init__.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel

import app.adapters.assetstock  # noqa: F401  (registers pexels/pixabay/unsplash)
import app.adapters.storage  # noqa: F401  (registers minio)
from app.core.deps import get_current_user
from app.models.user import User
from app.services.asset_service import (
    AssetFetchError,
    AssetService,
    AssetStockUnavailable,
    AssetValidationError,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])


class StockStatusResponse(BaseModel):
    active: bool
    providers: list[str]


class StockSearchResult(BaseModel):
    provider: str
    url: str
    thumb_url: str
    attribution: str = ""
    attribution_url: str = ""
    license: str
    width: str = ""
    height: str = ""


class AssetResponse(BaseModel):
    id: str
    provider: str
    license: str
    attribution_required: bool
    attribution_text: str | None = None
    storage_path: str
    content_hash: str
    reused: bool = False


class FetchStockRequest(BaseModel):
    url: str
    provider: str
    license: str
    attribution: str = ""
    attribution_required: bool = True


def _to_response(asset, *, reused: bool = False) -> AssetResponse:
    return AssetResponse(
        id=str(asset.id),
        provider=asset.provider,
        license=asset.license,
        attribution_required=asset.attribution_required,
        attribution_text=asset.attribution_text,
        storage_path=asset.storage_path,
        content_hash=asset.content_hash,
        reused=reused,
    )


@router.get("/stock-status", response_model=StockStatusResponse)
async def stock_status(
    request: Request,
    user: User = Depends(get_current_user),
):
    """BR-3: whether any asset_stock provider is currently usable.

    Role-appropriate messaging (admin -> link to Quản trị, creator -> "nhờ
    admin thêm key") is a frontend concern; this endpoint only exposes the
    boolean + provider list, no cost/sensitive data (unlike the admin-only
    /api/admin/providers matrix).
    """
    async with request.app.state.database.session() as db:
        svc = AssetService(db)
        return await svc.stock_status()


@router.get("/search", response_model=list[StockSearchResult])
async def search_stock(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    user: User = Depends(get_current_user),
):
    """BR-1: results carry license + source before selection is possible."""
    async with request.app.state.database.session() as db:
        svc = AssetService(db)
        try:
            return await svc.search(q)
        except AssetStockUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc


@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """BR-2: dedupe by content hash; validate type/size (10MB, jpg/png/webp)."""
    data = await file.read()
    async with request.app.state.database.session() as db:
        svc = AssetService(db)
        try:
            asset, reused = await svc.upload(
                data=data,
                content_type=file.content_type or "application/octet-stream",
                uploaded_by=str(user.id),
            )
        except AssetValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        await db.commit()
        return _to_response(asset, reused=reused)


@router.post("/fetch-stock", response_model=AssetResponse)
async def fetch_stock(
    payload: FetchStockRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """BR-4: Asset Worker downloads the stock result server-side into MinIO
    before any asset_id is assignable — render/preview never fetches the
    provider directly (rules/security.md)."""
    async with request.app.state.database.session() as db:
        svc = AssetService(db)
        try:
            asset = await svc.fetch_stock(
                url=payload.url,
                provider=payload.provider,
                license_=payload.license,
                attribution=payload.attribution,
                attribution_required=payload.attribution_required,
            )
        except AssetValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        except AssetFetchError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
            ) from exc
        await db.commit()
        return _to_response(asset)
