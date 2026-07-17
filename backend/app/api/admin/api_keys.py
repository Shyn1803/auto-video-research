"""Admin API key management — CRUD with masked responses.

RBAC: admin-only (require_role("admin") on every route).
Encryption: plaintext never leaves the request body until Fernet-encrypted in the service.
Validation: lightweight provider call before save (AC3).
Delete: consequence warning when last key of an active-chain provider is removed (BR-2).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import require_role
from app.core.crypto import mask
from app.core.exceptions import AllProvidersFailed
from app.models.api_key import ApiKey
from app.models.user import User

logger = logging.getLogger("avr.admin.api_keys")

router = APIRouter(prefix="/api/admin/api-keys", tags=["admin: api_keys"])


# ── Pydantic schemas (response shaping only, not DB models) ──────────────


class ApiKeyCreateRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=1, max_length=200)
    key: str = Field(..., min_length=4)

    @field_validator("provider")
    @classmethod
    def provider_snake(cls, v: str) -> str:
        return v.strip().lower()


class ApiKeyUpdateRequest(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=200)


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    label: str
    key_masked: str
    status: str
    usage_count: int
    last_used_at: str | None = None
    exhausted_until: str | None = None
    created_at: str
    updated_at: str


class ConsequenceResponse(BaseModel):
    warning: str | None = None
    chain_providers: list[str] = []


# ── helpers ──────────────────────────────────────────────────────────────


def _get_session(request: Request):
    return request.app.state.database.session()


def _row_to_response(row: ApiKey, plaintext: str | None = None) -> ApiKeyResponse:
    from app.services.api_key_service import KeyService  # local import avoids circular
    svc = KeyService(None)  # no factory needed for to_response
    data = svc.to_response(row, plaintext)
    return ApiKeyResponse(**data)


# ── endpoints ─────────────────────────────────────────────────────────────


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreateRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Create a new API key.

    Body must contain the plaintext key — it is Fernet-encrypted before
    persisting.  A lightweight provider call validates the key first;
    invalid → 400, nothing persisted (AC3).

    Save the request correlation for audit logging.
    """
    from app.core.config import get_settings

    settings = get_settings()

    # Step A — lightweight validation via adapter's available() check.
    # We resolve the chain to see if this provider is registered.
    from app.adapters.registry import get_adapter_class
    from app.adapters.base import ProviderSettings

    cls = get_adapter_class(body.provider, body.provider)
    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider %r is not registered" % body.provider,
        )

    # Instantiate adapter with proposed key and run its readiness check.
    adapter = cls(
        ProviderSettings(
            provider_name=body.provider,
            api_key=body.key,
        )
    )
    try:
        ok = await adapter.available()
    except Exception as exc:
        logger.warning(
            "api_key.validate_failed provider=%s user=%s error=%s",
            body.provider,
            current_user.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key không hợp lệ — provider could not validate the credential",
        )

    if not ok:
        logger.warning(
            "api_key.invalid provider=%s user=%s", body.provider, current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key không hợp lệ",
        )

    # Step B — persist encrypted.
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    row = await svc.create(
        provider=body.provider,
        label=body.label,
        plaintext_key=body.key,
    )

    logger.info(
        "api_key.created provider=%s label=%s id=%s by=%s",
        body.provider,
        body.label,
        row.id,
        current_user.id,
    )

    return _row_to_response(row, body.key)  # plaintext in memory only; masked in response


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """List all keys — response contains only masked values (BR-1)."""
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    rows = await svc.list_by_provider()
    return [_row_to_response(r) for r in rows]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Detail view — still masked, never plaintext (BR-1)."""
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    row = await svc.get_by_id(key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")
    # Decrypt to mask but NOT to reveal.
    plaintext = svc.get_plaintext(row)
    return _row_to_response(row, plaintext)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_label(
    key_id: str,
    body: ApiKeyUpdateRequest,
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Update only the label; the encrypted key is untouched."""
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    row = await svc.get_by_id(key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")

    if body.label is not None:
        async with _get_session(request) as session:
            row.label = body.label
            await session.commit()
            await session.refresh(row)

    plaintext = svc.get_plaintext(row)
    return _row_to_response(row, plaintext)


@router.delete("/{key_id}", response_model=ConsequenceResponse)
async def delete_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Delete with consequence check (BR-2).

    If this is the LAST active key for a provider that appears in any active
    chain, the response carries a ``warning`` field describing what breaks.
    Caller confirms delete via a separate action or frontend dialog.
    """
    from app.core.config import get_settings

    settings = get_settings()
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    row = await svc.get_by_id(key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")

    provider = row.provider
    # Check if this is the last key for this provider in an active chain.
    chain_vars = _chain_vars_for_provider(provider)
    active_chains = [
        var
        for var in chain_vars
        if provider in getattr(settings, var.lower(), "")
    ]
    # Count other active keys for this provider.
    all_keys = await svc.list_by_provider(provider)
    other_active = [
        k for k in all_keys if k.status == "active" and str(k.id) != key_id
    ]

    consequence: ConsequenceResponse | None = None
    if other_active:
        # Safe to delete — other keys remain.
        pass
    elif active_chains:
        consequence = ConsequenceResponse(
            warning=(
                f"Đang xoá key cuối của '{provider}'. Provider này đang trong "
                f"chain(s): {', '.join(active_chains)}. Xoá xong sẽ mất khả năng "
                f"tự động sử dụng {provider}."
            ),
            chain_providers=active_chains,
        )
        # Frontend/dialog should ask for explicit confirmation before
        # issuing the follow-up DELETE with a confirm header/query param.
        return consequence

    # No consequence / user confirmed — proceed.
    await svc.delete(key_id)
    logger.info("api_key.deleted id=%s provider=%s by=%s", key_id, provider, current_user.id)
    return ConsequenceResponse()


@router.post("/{key_id}/confirm-delete", response_model=ConsequenceResponse)
async def confirm_delete(
    key_id: str,
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Second step of delete-after-warning flow (BR-2).

    Client must have first called DELETE, received the warning, shown it
    to the user, and now calls POST to confirm.
    """
    from app.services.api_key_service import KeyService

    svc = KeyService(_get_session(request))
    row = await svc.get_by_id(key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")

    await svc.delete(key_id)
    logger.info(
        "api_key.confirm_deleted id=%s provider=%s by=%s",
        key_id,
        row.provider,
        current_user.id,
    )
    return ConsequenceResponse()


# ── internal helpers ──────────────────────────────────────────────────────


def _chain_vars_for_provider(provider: str) -> list[str]:
    """Return chain env var names that could contain *provider*."""
    return [
        "LLM_CHAIN_CHEAP",
        "LLM_CHAIN_STRONG",
        "LLM_CHAIN",
        "TTS_CHAIN",
        "TTS_CHAIN_CHEAP",
        "SEARCH_CHAIN",
        "IMAGE_GEN_CHAIN",
        "ASSET_CHAIN",
        "STORAGE_PROVIDER",
        "PUBLISH_PLATFORMS",
        "EMBEDDING_CHAIN",
    ]
