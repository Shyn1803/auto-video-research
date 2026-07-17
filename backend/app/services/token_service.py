"""Token lifecycle — issue, rotate, verify, reuse detection."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


class TokenService:
    """Create and validate JWT access tokens + persisted refresh tokens."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=7),
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def create_access_token(self, subject: str, role: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "role": role,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }
        import jwt as _jwt
        return _jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: UUID) -> tuple[str, UUID]:
        """Return (raw_token, family_id). Raw token is sent to client once."""
        import jwt as _jwt
        family_id = UUID(int=0)  # set below via uuid4

        from uuid import uuid4
        family_id = uuid4()
        now = datetime.now(timezone.utc)
        raw = f"{user_id}.{family_id.hex}.{int(now.timestamp())}"
        raw_token = _jwt.encode(
            {"sub": str(user_id), "fam": str(family_id), "iat": int(now.timestamp())},
            self._secret,
            algorithm=self._algorithm,
        )
        return raw_token, family_id

    def hash_token(self, raw: str) -> str:
        return sha256(raw.encode()).hexdigest()

    async def persist_refresh(
        self, session: AsyncSession, user_id: UUID, raw_token: str, family_id: UUID
    ) -> RefreshToken:
        tok_hash = self.hash_token(raw_token)
        now = datetime.now(timezone.utc)
        rt = RefreshToken(
            user_id=user_id,
            token_hash=tok_hash,
            family_id=str(family_id),
            expires_at=now + self._refresh_ttl,
        )
        session.add(rt)
        await session.flush()
        return rt

    async def revoke_all_for_user(self, session: AsyncSession, user_id: UUID) -> int:
        """Revoke every non-revoked refresh token for a user. Returns count revoked."""
        now = datetime.now(timezone.utc)
        result = await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return result.rowcount or 0

    async def rotate_refresh(
        self,
        session: AsyncSession,
        raw_token: str,
    ) -> tuple[str, str]:
        """Revoke used token, issue new raw_token + family_id string."""
        tok_hash = self.hash_token(raw_token)
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == tok_hash)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
        if existing.revoked_at is not None:
            # Reuse detected — revoke entire family
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == existing.family_id)
                .where(RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            await session.flush()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token reuse detected — all sessions revoked",
            )
        # Mark used token as revoked (one-time use)
        existing.revoked_at = now
        # Issue new token in same family
        fam = existing.family_id
        user_id = existing.user_id
        new_raw, _ = self.create_refresh_token(user_id)
        await self.persist_refresh(session, user_id, new_raw, UUID(fam))
        await session.flush()
        return new_raw, fam
