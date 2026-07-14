"""TokenService - rotate, reuse detection (AC-1, AC-2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.token_service import TokenService

SECRET = "test-secret"


def make_service() -> TokenService:
    return TokenService(secret=SECRET)


def make_row(user_id, family_id, revoked=None):
    """Stand-in RefreshToken ORM row."""
    return SimpleNamespace(
        user_id=user_id,
        family_id=str(family_id),
        token_hash="",
        revoked_at=revoked,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )


def mock_session(first_row):
    session = AsyncMock()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = first_row
    session.execute = AsyncMock(return_value=r1)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session, r1


# AC-1: happy rotate

@pytest.mark.asyncio
async def test_rotate_refresh_issues_new_token() -> None:
    """AC-1: rotate revokes old token and issues a new one."""
    svc = make_service()
    user_id = uuid.uuid4()
    fam = uuid.uuid4()
    raw_old, _ = svc.create_refresh_token(user_id)
    row = make_row(user_id, fam)
    session, _ = mock_session(row)

    new_raw, ret_fam = await svc.rotate_refresh(session, raw_old)

    assert new_raw != raw_old
    assert row.revoked_at is not None
    assert str(ret_fam) == str(fam)
    session.flush.assert_called()


@pytest.mark.asyncio
async def test_rotate_reuse_revokes_entire_chain() -> None:
    """AC-2: reusing a rotated token revokes the whole family."""
    svc = make_service()
    user_id = uuid.uuid4()
    fam = uuid.uuid4()
    raw_old, _ = svc.create_refresh_token(user_id)

    reused = make_row(user_id, fam, revoked=datetime.now(timezone.utc))
    reused.token_hash = svc.hash_token(raw_old)

    session = AsyncMock()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = reused
    r2 = MagicMock()
    session.execute = AsyncMock(side_effect=[r1, r2])
    session.flush = AsyncMock()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await svc.rotate_refresh(session, raw_old)

    assert exc_info.value.status_code == 401
    assert "reuse" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_unknown_token_returns_401() -> None:
    """AC-2: unknown refresh token returns 401."""
    svc = make_service()
    session = AsyncMock()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=r1)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await svc.rotate_refresh(session, "invalid-token")

    assert exc_info.value.status_code == 401


