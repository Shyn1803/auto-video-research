"""Admin user management endpoints — CRUD with safety guards (BR-1, BR-2, BR-3)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import require_role
from app.core.security import hash_password
from app.models.user import User
from app.services.token_service import TokenService
from app.services.user_admin_service import UserAdminService

router = APIRouter(tags=["admin-users"])

_tokens = TokenService(secret="")  # placeholder, only used for revoke tokens


class UserCreateReq(BaseModel):
    email: str
    display_name: str
    password: str
    role: str = "creator"


class UserRoleUpdate(BaseModel):
    role: str


class UserLockUpdate(BaseModel):
    is_active: bool


class UserAdminOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    must_change_password: bool


def _to_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
    )


@router.get("/users", response_model=list[UserAdminOut])
async def list_users(req: Request, _auth=Depends(require_role("admin"))) -> list[UserAdminOut]:
    async with req.app.state.database.session() as session:
        svc = UserAdminService(db=session, token_service=_tokens)
        users = await svc.list()
        await session.commit()
    return [_to_out(u) for u in users]


@router.post("/users", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
async def create_user(req: Request, body: UserCreateReq, _auth=Depends(require_role("admin"))) -> UserAdminOut:
    async with req.app.state.database.session() as session:
        svc = UserAdminService(db=session, token_service=_tokens)
        user = await svc.create(
            email=body.email,
            display_name=body.display_name,
            role=body.role,
            temp_password=body.password,
        )
        await session.commit()
    return _to_out(user)


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_role(
    req: Request,
    user_id: UUID,
    body: UserRoleUpdate,
    actor=Depends(require_role("admin")),
) -> UserAdminOut:
    async with req.app.state.database.session() as session:
        svc = UserAdminService(db=session, token_service=_tokens)
        user = await svc.set_role(user_id, actor_id=actor.id, new_role=body.role)
        await session.commit()
    return _to_out(user)


@router.patch("/users/{user_id}/lock", response_model=UserAdminOut)
async def lock_unlock(
    req: Request,
    user_id: UUID,
    body: UserLockUpdate,
    actor=Depends(require_role("admin")),
) -> UserAdminOut:
    async with req.app.state.database.session() as session:
        svc = UserAdminService(db=session, token_service=_tokens)
        if body.is_active:
            user = await svc.unlock(user_id)
        else:
            user = await svc.lock(user_id, actor_id=actor.id)
        await session.commit()
    return _to_out(user)
