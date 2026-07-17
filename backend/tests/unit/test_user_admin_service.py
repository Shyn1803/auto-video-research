"""Unit tests for UserAdminService — covers 1-7 ACs (BR-1 self-lock, BR-2 token revoke, BR-3 last-admin)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.user_admin_service import UserAdminService


def _user(role="creator", active=True, uid=None):
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = role
    u.is_active = active
    u.created_at = datetime.now(UTC)
    return u


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        m = MagicMock()
        m.all.return_value = self._rows
        return m


class _FakeSession:
    """Minimal AsyncSession stand-in: returns `rows` for every select, ignores flush/add."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.flush = AsyncMock()
        self.add = MagicMock()

    async def execute(self, stmt, *a, **kw):
        return _FakeResult(self.rows)


@pytest.fixture()
def tokens():
    t = MagicMock()
    t.revoke_all_for_user = AsyncMock(return_value=2)
    return t


# ── create() sets must_change_password=True (AC: temp password forces reset) ──


@pytest.mark.asyncio
async def test_create_sets_must_change_password(tokens):
    session = _FakeSession()
    svc = UserAdminService(db=session, token_service=tokens)
    user = await svc.create(email="a@b.com", display_name="A", role="creator", temp_password="temp123456")
    assert user.must_change_password is True
    session.add.assert_called_once()


# ── BR-1: cannot change own role / cannot lock self ────────────────────────────


@pytest.mark.asyncio
async def test_set_role_rejects_self(tokens):
    session = _FakeSession()
    svc = UserAdminService(db=session, token_service=tokens)
    uid = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        await svc.set_role(uid, actor_id=uid, new_role="admin")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_lock_rejects_self(tokens):
    session = _FakeSession()
    svc = UserAdminService(db=session, token_service=tokens)
    uid = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        await svc.lock(uid, actor_id=uid)
    assert exc.value.status_code == 400


# ── BR-2: locking revokes all refresh tokens ────────────────────────────────────


@pytest.mark.asyncio
async def test_lock_revokes_tokens(tokens):
    target = _user(role="creator", active=True)
    session = _FakeSession(rows=[target])
    svc = UserAdminService(db=session, token_service=tokens)
    result = await svc.lock(target.id, actor_id=uuid.uuid4())
    assert result.is_active is False
    tokens.revoke_all_for_user.assert_awaited_once_with(session, target.id)


@pytest.mark.asyncio
async def test_lock_already_locked_rejected(tokens):
    target = _user(role="creator", active=False)
    session = _FakeSession(rows=[target])
    svc = UserAdminService(db=session, token_service=tokens)
    with pytest.raises(HTTPException) as exc:
        await svc.lock(target.id, actor_id=uuid.uuid4())
    assert exc.value.status_code == 400


# ── BR-3: last active admin cannot be locked or demoted ─────────────────────────


@pytest.mark.asyncio
async def test_lock_last_admin_rejected(tokens):
    admin = _user(role="admin", active=True)
    # _get returns [admin]; _count_active_admins (exclude=admin.id) also uses rows, so
    # simulate "no other admins" by using a session whose rows list is just [admin]
    # (the exclude filter is expressed in the SQL, our fake session ignores WHERE clauses,
    # so we model "0 other admins" by returning an empty list for the second query).
    session = _FakeSession(rows=[admin])
    svc = UserAdminService(db=session, token_service=tokens)

    call_count = {"n": 0}
    orig_execute = session.execute

    async def execute_seq(stmt, *a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeResult([admin])  # _get
        return _FakeResult([])  # _count_active_admins → 0 other active admins

    session.execute = execute_seq

    with pytest.raises(HTTPException) as exc:
        await svc.lock(admin.id, actor_id=uuid.uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_set_role_demote_last_admin_rejected(tokens):
    admin = _user(role="admin", active=True)
    session = _FakeSession(rows=[admin])
    svc = UserAdminService(db=session, token_service=tokens)

    call_count = {"n": 0}

    async def execute_seq(stmt, *a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeResult([admin])  # _get
        return _FakeResult([])  # _count_active_admins → 0 other active admins

    session.execute = execute_seq

    with pytest.raises(HTTPException) as exc:
        await svc.set_role(admin.id, actor_id=uuid.uuid4(), new_role="creator")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_lock_admin_allowed_when_another_admin_active(tokens):
    admin = _user(role="admin", active=True)
    other_admin = _user(role="admin", active=True)
    session = _FakeSession(rows=[admin])
    svc = UserAdminService(db=session, token_service=tokens)

    call_count = {"n": 0}

    async def execute_seq(stmt, *a, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _FakeResult([admin])
        return _FakeResult([other_admin])  # another active admin exists

    session.execute = execute_seq

    result = await svc.lock(admin.id, actor_id=uuid.uuid4())
    assert result.is_active is False


# ── unlock() re-activates without touching role/tokens ──────────────────────────


@pytest.mark.asyncio
async def test_unlock_reactivates(tokens):
    target = _user(role="creator", active=False)
    session = _FakeSession(rows=[target])
    svc = UserAdminService(db=session, token_service=tokens)
    result = await svc.unlock(target.id)
    assert result.is_active is True
