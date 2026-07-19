"""Shared test fixtures — fake database + user factories for auth endpoint tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import hash_password
from app.main import create_app


# ── User factory ─────────────────────────────────────────────────────────────


def _make_user(uid, email, password, role, *, active=True):
    """Build a User stand-in using MagicMock (avoids SQLAlchemy __new__ issues)."""
    u = MagicMock()
    u.id = uid
    u.email = email
    u.password_hash = hash_password(password)
    u.display_name = email.split("@")[0]
    u.role = role
    u.is_active = active
    u.created_at = datetime.now(UTC)
    u.updated_at = datetime.now(UTC)
    return u


ADMIN_USER = _make_user(
    uuid.UUID("11111111-1111-1111-1111-111111111111"),
    "admin@test.com",
    "admin123",
    "admin",
)
CREATOR_USER = _make_user(
    uuid.UUID("22222222-2222-2222-2222-222222222222"),
    "creator@test.com",
    "creator123",
    "creator",
)
LOCKED_USER = _make_user(
    uuid.UUID("33333333-3333-3333-3333-333333333333"),
    "locked@test.com",
    "locked123",
    "creator",
    active=False,
)


# ── Fake database ─────────────────────────────────────────────────────────────


class FakeDatabase:
    """Drop-in replacement for app.state.database in tests."""

    def __init__(self, session_cm):
        self._cm = session_cm

    async def check(self) -> None:
        return None

    async def close(self) -> None:
        return None

    def session(self):
        """Used as: async with db.session() as session: ..."""
        return self._cm


def _make_session_cm(user_row=None, rt_row=None):
    """Closure-bound session CM so injected rows live on captured cells."""
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.close = AsyncMock()

    async def _get(model, pk):
        return user_row

    session.get = _get

    async def _execute(stmt, *a, **kw):
        r = MagicMock()
        try:
            cols = list(stmt.columns_clause_froms)
            model = cols[0][0].class_ if cols else None
            if model is not None and model.__name__ == "ApiKey":
                rows = [rt_row] if rt_row else []
            else:
                rows = [user_row] if user_row else []
        except Exception:
            rows = [user_row] if user_row else []
        r.scalar_one_or_none = MagicMock(return_value=None)
        r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=rows)))
        return r

    async def _scalars(stmt):
        return await _execute(stmt)

    session.execute = _execute
    session.scalars = _scalars

    class _CM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    return _CM()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def app():
    a = create_app()
    a.state.settings = get_settings()  # needed for deps.py / security.py
    return a


@pytest.fixture()
def admin_client(app):
    """FastAPI TestClient whose DB returns ADMIN_USER on user queries."""
    app.state.database = FakeDatabase(_make_session_cm(ADMIN_USER))
    return TestClient(app)


@pytest.fixture()
def creator_client(app):
    """FastAPI TestClient whose DB returns CREATOR_USER on user queries."""
    app.state.database = FakeDatabase(_make_session_cm(CREATOR_USER))
    return TestClient(app)


@pytest.fixture()
def locked_client(app):
    """FastAPI TestClient whose DB returns LOCKED_USER (is_active=False)."""
    app.state.database = FakeDatabase(_make_session_cm(LOCKED_USER))
    return TestClient(app)
