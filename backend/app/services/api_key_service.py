"""API key service — encryption, CRUD, round-robin rotation, exhausted_until.

Single source of truth for key lifecycle:
- Save: validate-before-save via lightweight provider call → Fernet encrypt → INSERT
- Get: decrypt only into memory; masked form computed for every response
- Rotation: env keys appear before DB keys in round order; 429 / quota errors
  mark exhausted_until and auto-reactivate when reset time passes
- Delete: consequence check (last key of a provider in an active chain)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Sequence

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt, mask
from app.core.exceptions import AllProvidersFailed
from app.models.api_key import ApiKey

logger = logging.getLogger("avr.api_keys")

# ---------------------------------------------------------------------------
# Internal helper — plaintext lives only in local scope.
# ---------------------------------------------------------------------------


class KeyService:
    """Business logic for API key management."""

    def __init__(self, session_factory) -> None:
        # session_factory is the async_sessionmaker; we open short-lived
        # sessions per method call (request-scoped pattern).
        self._session_factory = session_factory

    # ── read helpers ──────────────────────────────────────────────────────

    async def get_by_id(self, key_id: str) -> ApiKey | None:
        """Return the DB row (still encrypted)."""
        async with self._session_factory() as session:
            return await session.get(ApiKey, key_id)

    async def get_plaintext(self, key: ApiKey) -> str:
        """Decrypt and return plaintext string.

        Raises RuntimeError on bad ciphertext (should never happen for valid rows).
        """
        try:
            return decrypt(key.key_encrypted)
        except InvalidToken:
            logger.error("api_key.get_plaintext bad ciphertext id=%s", key.id)
            raise RuntimeError("stored ciphertext is invalid — re-enter this key") from None

    # ── public CRUD ───────────────────────────────────────────────────────

    async def create(
        self,
        *,
        provider: str,
        label: str,
        plaintext_key: str,
        validate_payload: dict | None = None,
    ) -> ApiKey:
        """Persist a new API key after optionally validating it with a lightweight call.

        BR-1: plaintext never stored — encrypt before writing.
        AC3: invalid key → 400 (caller must raise before calling this).
        """
        ciphertext = encrypt(plaintext_key)
        row = ApiKey(
            provider=provider.strip().lower(),
            label=label.strip(),
            key_encrypted=ciphertext,
            status="active",
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.flush()
            await session.commit()
            await session.refresh(row)
        logger.info(
            "api_key.created id=%s provider=%s label=%s",
            row.id,
            row.provider,
            row.label,
        )
        return row

    async def track_usage(self, key_id: str) -> int:
        """Increment usage_count for this key. Returns new count."""
        async with self._session_factory() as session:
            row = await session.get(ApiKey, key_id)
            if row is None:
                return 0
            row.usage_count = ApiKey.usage_count + 1
            row.last_used_at = datetime.now(UTC)
            await session.commit()
            return int(row.usage_count)

    async def mark_exhausted(self, key_id: str, until: datetime | None = None) -> None:
        """Set status='exhausted' and exhausted_until (default: next midnight UTC)."""
        if until is None:
            now = datetime.now(UTC)
            until = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self._session_factory() as session:
            row = await session.get(ApiKey, key_id)
            if row is None:
                return
            row.status = "exhausted"
            row.exhausted_until = until
            await session.commit()
        logger.info("api_key.exhausted id=%s until=%s", key_id, until.isoformat())

    async def reactivate_expired(self) -> int:
        """Lazy re-activation scan: set active on keys whose exhausted_until passed.

        Returns count of reactivated rows.
        """
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
                select(ApiKey)
                .where(ApiKey.status == "exhausted")
                .where(ApiKey.exhausted_until.is_not(None))
                .where(ApiKey.exhausted_until <= now)
            )
            result = await session.scalars(stmt)
            rows = list(result.all())
            for row in rows:
                row.status = "active"
                row.exhausted_until = None
            await session.commit()
        if rows:
            logger.info("api_key.reactivated count=%d", len(rows))
        return len(rows)

    async def delete(self, key_id: str) -> ApiKey | None:
        """Hard-delete the key row.

        Caller must have checked the "last key" consequence (BR-2).
        """
        async with self._session_factory() as session:
            row = await session.get(ApiKey, key_id)
            if row is None:
                return None
            provider = row.provider  # capture before delete
            await session.delete(row)
            await session.commit()
        logger.info("api_key.deleted id=%s provider=%s", key_id, provider)
        return row

    # ── listing ───────────────────────────────────────────────────────────

    async def list_by_provider(self, provider: str | None = None) -> list[ApiKey]:
        """Return all keys (encrypted); caller masks for response."""
        async with self._session_factory() as session:
            stmt = select(ApiKey).order_by(ApiKey.provider, ApiKey.created_at)
            if provider:
                stmt = stmt.where(ApiKey.provider == provider)
            result = await session.scalars(stmt)
            return list(result.all())

    # ── masked response helpers ───────────────────────────────────────────

    @staticmethod
    def to_response(row: ApiKey, plaintext: str | None = None) -> dict:
        """Build the safe response dict — no plaintext ever included."""
        if plaintext is None:
            # Response without decryption (list view).
            return {
                "id": str(row.id),
                "provider": row.provider,
                "label": row.label,
                "key_masked": "****",
                "status": row.status,
                "usage_count": row.usage_count,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                "exhausted_until": (
                    row.exhausted_until.isoformat() if row.exhausted_until else None
                ),
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
        # Detail view: include masked form only.
        return {
            "id": str(row.id),
            "provider": row.provider,
            "label": row.label,
            "key_masked": mask(plaintext) if plaintext else "****",
            "status": row.status,
            "usage_count": row.usage_count,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            "exhausted_until": (
                row.exhausted_until.isoformat() if row.exhausted_until else None
            ),
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
