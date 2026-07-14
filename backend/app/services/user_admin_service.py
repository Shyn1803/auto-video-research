"""Admin user lifecycle — create, list, role change, lock/unlock.

Business rules enforced at the service layer (BR-1: no self-lock/demote;
BR-2: lock revokes all refresh tokens; BR-3: always >= 1 active admin).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, validate_password
from app.models.refresh_token import RefreshToken
from app.models.user import User

ALLOWED_ROLES: tuple[str, ...] = ("admin", "creator")
_MIN_PASSWORD_LENGTH: int = 10


class UserAdminService:
	"""Service for admin-only user management."""

	def __init__(self, session: AsyncSession, acting_user_id: str) -> None:
		self._session = session
		self._acting_user_id = acting_user_id

	# -- internal helpers ----------------------------------------------------

	async def _count_active_admins(self) -> int:
		result = await self._session.execute(
			select(func.count())
			.select_from(User)
			.where(User.role == "admin")
			.where(User.is_active.is_(True)),
		)
		return result.scalar_one()

	async def _ensure_acting_user(self) -> User:
		result = await self._session.execute(
			select(User).where(User.id == self._acting_user_id),
		)
		user = result.scalar_one_or_none()
		if user is None:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="acting user not found",
			)
		return user

	def _assert_not_self(self, target_id: str, action: str) -> None:
		if target_id == self._acting_user_id:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=f"cannot {action} yourself",
			)

	async def _ensure_last_admin(self, target_id: str) -> None:
		self._assert_not_self(target_id, "deactivate/demote")
		count = await self._count_active_admins()
		if count <= 1:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="at least one active admin is required",
			)

	async def _revoke_all_refresh_tokens(self, user_id: str) -> None:
		now = datetime.now(UTC)
		await self._session.execute(
			update(RefreshToken)
			.where(RefreshToken.user_id == user_id)
			.where(RefreshToken.revoked_at.is_(None))
			.values(revoked_at=now),
		)

	# -- public API ----------------------------------------------------------

	async def create_user(
		self,
		*,
		email: str,
		display_name: str,
		temp_password: str,
		role: str = "creator",
	) -> User:
		"""Create a user with a temp password that must be changed on first login."""
		if role not in ALLOWED_ROLES:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"role must be one of {ALLOWED_ROLES}",
			)
		try:
			validate_password(temp_password)
		except ValueError as exc:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=str(exc),
			) from exc

		existing = await self._session.scalar(
			select(User).where(User.email == email),
		)
		if existing is not None:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="email already exists",
			)

		user = User(
			email=email,
			password_hash=hash_password(temp_password),
			display_name=display_name,
			role=role,
			is_active=True,
			must_change_password=True,
		)
		self._session.add(user)
		await self._session.flush()
		return user

	async def list_users(
		self, page: int = 1, size: int = 20
	) -> tuple[Sequence[User], int]:
		page = max(page, 1)
		size = max(min(size, 100), 1)
		total_result = await self._session.execute(
			select(func.count()).select_from(User),
		)
		total = total_result.scalar_one()

		result = await self._session.execute(
			select(User)
			.order_by(User.created_at.desc())
			.offset((page - 1) * size)
			.limit(size),
		)
		items = result.scalars().all()
		return items, total

	async def update_role(self, user_id: str, new_role: str) -> User:
		"""Change a users role; rejects invalid role or demoting the last admin."""
		await self._ensure_last_admin(user_id)
		if new_role not in ALLOWED_ROLES:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=f"role must be one of {ALLOWED_ROLES}",
			)
		result = await self._session.execute(
			select(User).where(User.id == user_id),
		)
		user = result.scalar_one_or_none()
		if user is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="user not found",
			)
		self._assert_not_self(user_id, "demote")
		user.role = new_role
		user.updated_at = datetime.now(UTC)
		await self._session.flush()
		return user

	async def lock_user(self, user_id: str) -> User:
		"""Lock a user; revokes all refresh tokens immediately."""
		await self._ensure_last_admin(user_id)
		result = await self._session.execute(
			select(User).where(User.id == user_id),
		)
		user = result.scalar_one_or_none()
		if user is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="user not found",
			)
		if not user.is_active:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="user is already locked",
			)
		user.is_active = False
		user.updated_at = datetime.now(UTC)
		await self._revoke_all_refresh_tokens(user_id)
		await self._session.flush()
		return user

	async def unlock_user(self, user_id: str) -> User:
		"""Re-enable a locked user."""
		result = await self._session.execute(
			select(User).where(User.id == user_id),
		)
		user = result.scalar_one_or_none()
		if user is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="user not found",
			)
		if user.is_active:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="user is already active",
			)
		user.is_active = True
		user.updated_at = datetime.now(UTC)
		await self._session.flush()
		return user
