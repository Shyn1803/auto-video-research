"""Admin user management endpoints (admin only)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.core.deps import require_role
from app.core.security import hash_password, validate_password
from app.models.user import User
from app.services.user_admin_service import UserAdminService

router = APIRouter(tags=["users"])


# -- schemas ---------------------------------------------------------------

class CreateUserBody(BaseModel):
	email: EmailStr
	display_name: str
	password: str  # temp password
	role: str = "creator"


class UpdateRoleBody(BaseModel):
	role: str


class UserOut(BaseModel):
	id: str
	email: str
	display_name: str
	role: str
	is_active: bool
	must_change_password: bool
	created_at: str
	updated_at: str

	@classmethod
	def from_model(cls, u: User) -> "UserOut":
		return cls(
			id=str(u.id),
			email=u.email,
			display_name=u.display_name,
			role=u.role,
			is_active=u.is_active,
			must_change_password=u.must_change_password,
			created_at=u.created_at.isoformat(),
			updated_at=u.updated_at.isoformat(),
		)


class ListResponse(BaseModel):
	items: list[UserOut]
	total: int
	page: int
	size: int


class ChangePasswordBody(BaseModel):
	new_password: str


# -- endpoints -------------------------------------------------------------

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
	req: Request,
	body: CreateUserBody,
	_admin: User = Depends(require_role("admin")),
) -> UserOut:
	async with req.app.state.database.session() as session:
		svc = UserAdminService(session, str(_admin.id))
		user = await svc.create_user(
			email=str(body.email),
			display_name=body.display_name,
			temp_password=body.password,
			role=body.role,
		)
		return UserOut.from_model(user)


@router.get("/users")
async def list_users(
	req: Request,
	page: int = 1,
	size: int = 20,
	_admin: User = Depends(require_role("admin")),
) -> ListResponse:
	async with req.app.state.database.session() as session:
		svc = UserAdminService(session, str(_admin.id))
		items, total = await svc.list_users(page=page, size=size)
		return ListResponse(
			items=[UserOut.from_model(u) for u in items],
			total=total, page=page, size=size,
		)


@router.patch("/users/{user_id}")
async def update_user_role(
	req: Request,
	user_id: str,
	body: UpdateRoleBody,
	_admin: User = Depends(require_role("admin")),
) -> UserOut:
	async with req.app.state.database.session() as session:
		svc = UserAdminService(session, str(_admin.id))
		user = await svc.update_role(user_id, body.role)
		return UserOut.from_model(user)


@router.post("/users/{user_id}/lock")
async def lock_user(
	req: Request,
	user_id: str,
	_admin: User = Depends(require_role("admin")),
) -> UserOut:
	async with req.app.state.database.session() as session:
		svc = UserAdminService(session, str(_admin.id))
		user = await svc.lock_user(user_id)
		return UserOut.from_model(user)


@router.post("/users/{user_id}/unlock")
async def unlock_user(
	req: Request,
	user_id: str,
	_admin: User = Depends(require_role("admin")),
) -> UserOut:
	async with req.app.state.database.session() as session:
		svc = UserAdminService(session, str(_admin.id))
		user = await svc.unlock_user(user_id)
		return UserOut.from_model(user)


@router.post("/auth/change-password")
async def change_password(
	req: Request,
	body: ChangePasswordBody,
	user: User = Depends(get_current_user),
) -> dict[str, str]:
	"""Change the current user's password (clears must_change_password flag)."""
	try:
		validate_password(body.new_password)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=str(exc),
		) from exc
	async with req.app.state.database.session() as session:
		result = await session.execute(
			select(User).where(User.id == user.id),
		)
		db_user = result.scalar_one_or_none()
		if db_user is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="user not found",
			)
		db_user.password_hash = hash_password(body.new_password)
		db_user.must_change_password = False
		db_user.updated_at = datetime.now(UTC)
		await session.flush()
	return {"detail": "password changed"}
