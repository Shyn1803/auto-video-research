"""Auth endpoints — login, refresh, logout, me."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy import update
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
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
    return TokenResponse(access_token=access)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    raw = request.cookies.get("refresh_token")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no refresh token")
    async with request.app.state.database.session() as session:
        new_raw, _ = await _tokens.rotate_refresh(session, raw)
        await session.commit()
    payload = _tokens.hash_token(new_raw)  # get user from store
    async with request.app.state.database.session() as session:
        from sqlalchemy import select
        result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == payload))
        rt = result.scalar_one_or_none()
    user_id = UUID(rt.user_id) if rt else None
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh")
    async with request.app.state.database.session() as session:
        result2 = await session.execute(select(User).where(User.id == user_id))
        user = result2.scalar_one_or_none()
    access = _tokens.create_access_token(subject=str(user.id), role=user.role)
    response.set_cookie("refresh_token", new_raw, httponly=True, secure=False, samesite="lax", max_age=_s.refresh_token_expire_days * 24 * 3600)
    return TokenResponse(access_token=access)


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    raw = request.cookies.get("refresh_token")
    if raw:
        async with request.app.state.database.session() as session:
            tok_hash = _tokens.hash_token(raw)
            await session.execute(
                update(RefreshToken).where(RefreshToken.token_hash == tok_hash).values(revoked_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
            )
            await session.commit()
    response.delete_cookie("refresh_token")
    return {"detail": "logged out"}


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(_deps.get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, display_name=user.display_name, role=user.role)
