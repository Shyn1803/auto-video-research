"""Auth endpoints — login, refresh, logout, me, change-password."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.deps import get_current_user, require_role
from app.core.rate_limit import limiter
from app.core.security import (
    hash_password,
    verify_password,
    validate_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.token_service import TokenService

router = APIRouter(tags=["auth"])
_s = get_settings()
_tokens = TokenService(secret=_s.jwt_secret)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: Request, body: LoginRequest, response: Response) -> TokenResponse:
    ok, retry_after = limiter.check(body.email, req.client.host if req.client else "unknown")
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"too many failed attempts, retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )
    async with req.app.state.database.session() as session:
        result = await session.execute(select(User).where(User.email == str(body.email)))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(body.password, user.password_hash):
            limiter.record(body.email, req.client.host if req.client else "unknown")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        limiter.check(body.email, req.client.host if req.client else "unknown")  # reset on success
        access = _tokens.create_access_token(subject=str(user.id), role=user.role)
        refresh_raw, family_id = _tokens.create_refresh_token(user.id)
        async with req.app.state.database.session() as session:
            await _tokens.persist_refresh(session, user.id, refresh_raw, family_id)
            await session.commit()
        response.set_cookie(
            "refresh_token",
            refresh_raw,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=_s.refresh_token_expire_days * 24 * 3600,
        )
        return TokenResponse(
            access_token=access,
            must_change_password=user.must_change_password,
        )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    raw = request.cookies.get("refresh_token")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no refresh token")
    async with request.app.state.database.session() as session:
        new_raw, _ = await _tokens.rotate_refresh(session, raw)
        await session.commit()
        payload = _tokens.hash_token(new_raw)
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == payload)
        )
        rt = result.scalar_one_or_none()
        user_id = UUID(rt.user_id) if rt else None
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh")
        result2 = await session.execute(select(User).where(User.id == user_id))
        user = result2.scalar_one_or_none()
    access = _tokens.create_access_token(subject=str(user.id), role=user.role)
    response.set_cookie(
        "refresh_token",
        new_raw,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=_s.refresh_token_expire_days * 24 * 3600,
    )
    return TokenResponse(
        access_token=access,
        must_change_password=user.must_change_password if user else False,
    )


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    raw = request.cookies.get("refresh_token")
    if raw:
        tok_hash = _tokens.hash_token(raw)
        await request.app.state.database.session().execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == tok_hash)
            .values(
                revoked_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                )
            )
        )
        await request.app.state.database.session().commit()
    response.delete_cookie("refresh_token")
    return {"detail": "logged out"}


@router.post("/auth/change-password", tags=["auth"])
async def change_password(
    req: Request,
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    async with req.app.state.database.session() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one_or_none()
        if db_user is None or not verify_password(body.old_password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid old password"
            )
        try:
            validate_password(body.new_password)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            )
        db_user.password_hash = hash_password(body.new_password)
        db_user.must_change_password = False
        await session.commit()
    return {"detail": "password changed"}


@router.get("/auth/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


@router.get("/auth/admin/ping", tags=["_test_rbac"])
async def _admin_ping(user: User = Depends(require_role("admin"))) -> dict:
    return {"detail": "admin OK"}
