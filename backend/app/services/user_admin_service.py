"""Admin user management — CRUD with safety guards (BR-1, BR-2, BR-3)."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


class UserAdminService:
    """Admin CRUD for users.

    BR-1: Cannot lock/demote self.
    BR-2: Locking a user revokes all refresh tokens immediately.
    BR-3: Must always have >= 1 active admin — operations that would drop to 0 rejected.
    """

    def __init__(self, db: AsyncSession, token_service: TokenService | None = None) -> None:
        self._db = db
        self._tokens = token_service or TokenService(secret="")

    async def list(self, *, include_locked: bool = True) -> list[User]:
        q = select(User)
        if not include_locked:
            q = q.where(User.is_active.is_(True))
        result = await self._db.execute(q.order_by(User.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, *, email: str, display_name: str, role: str, temp_password: str) -> User:
        from app.core.security import hash_password

        user = User(
            email=email,
            display_name=display_name,
            role=role,
            password_hash=hash_password(temp_password),
            must_change_password=True,
        )
        self._db.add(user)
        await self._db.flush()
        return user

    async def set_role(self, user_id: UUID, actor_id: UUID, new_role: str) -> User:
        if user_id == actor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )
        # BR-3: changing away from admin — check we're not the last one
        user = await self._get(user_id)
        if user.role == "admin" and new_role != "admin":
            active_admins = await self._count_active_admins(exclude=user_id)
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot demote the last active admin. Promote another user first.",
                )
        user.role = new_role
        await self._db.flush()
        return user

    async def lock(self, user_id: UUID, actor_id: UUID) -> User:
        if user_id == actor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot lock yourself",
            )
        user = await self._get(user_id)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already locked")
        # BR-3: locking an admin — are they the last?
        if user.role == "admin":
            active_admins = await self._count_active_admins(exclude=user_id)
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot lock the last active admin. Promote another user first.",
                )
        user.is_active = False
        # BR-2: revoke all refresh tokens immediately
        revoked = await self._tokens.revoke_all_for_user(self._db, user_id)
        logger.info("locked user %s, revoked %d tokens", user_id, revoked)
        await self._db.flush()
        return user

    async def unlock(self, user_id: UUID) -> User:
        user = await self._get(user_id)
        user.is_active = True
        await self._db.flush()
        return user

    async def force_password_reset(self, user_id: UUID) -> None:
        """Set must_change_password so next login requires a new password."""
        await self._db.execute(
            update(User).where(User.id == user_id).values(must_change_password=True)
        )
        await self._db.flush()

    async def _get(self, user_id: UUID) -> User:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _count_active_admins(self, exclude: UUID) -> int:
        result = await self._db.execute(
            select(User).where(User.role == "admin", User.is_active.is_(True), User.id != exclude)
        )
        return len(result.scalars().all())
