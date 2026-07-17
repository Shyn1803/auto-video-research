"""Integration tests for task 1-7 (Admin User Management).

AC-1  create creator + temp password → login → must_change_password=true → forced change → false
AC-2  lock a logged-in user → next request within 60s → 401
AC-3  lock the last active admin → 409 with explanation
AC-4  creator hitting /users or /auth/admin/ping → 403
AC-5  self-row lock/role controls disabled (UI-level; tested via service self-lock guard)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.main import create_app


ADMIN_ID = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))
CREATOR_ID = str(uuid.UUID("22222222-2222-2222-2222-222222222222"))
ONLY_ADMIN_ID = str(uuid.UUID("33333333-3333-3333-3333-333333333333"))


def _make_user_row(**overrides):
	defaults = dict(
		id=uuid.UUID(ADMIN_ID), email="admin@test.com",
		password_hash=hash_password("admin123"),
		display_name="Test Admin", role="admin",
		is_active=True, must_change_password=False,
		created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
	)
	defaults.update(overrides)
	u = MagicMock()
	for k, v in defaults.items():
		setattr(u, k, v)
	return u


def _admin_client(app, user):
	app.state.database = _FakeDB(user)
	return TestClient(app)


def _auth_header(user_id: str, role: str = "admin") -> dict:
	secret = get_settings().jwt_secret
	token = create_access_token(subject=user_id, role=role, secret=secret)
	return {"Authorization": f"Bearer {token}"}


# --- fixtures for auth.py (user query only) ---------------------------------
_LOGIN_USER = _make_user_row(
	id=uuid.UUID(ADMIN_ID), email="creator@temp.test",
	password_hash=hash_password("TempPass123!"),
	role="creator", must_change_password=True,
)


class _AuthFakeDB:
	def __init__(self, user):
		self.user = user

	def session(self):
		s = MagicMock()
		s.commit = MagicMock()
		s.add = MagicMock()
		s.flush = MagicMock()

		async def _get(model, pk):
			return self.user

		async def _exec_login(stmt, *_a, **_kw):
			# str(stmt) contains "users WHERE users.email"
			q = str(stmt).lower()
			if "email" in q:
				r = MagicMock()
				r.scalar_one_or_none.return_value = self.user
				r.scalars.return_value.all.return_value = [self.user]
				return r
			from sqlalchemy import select as sa_select
			r = MagicMock()
			r.scalar_one_or_none.return_value = None
			return r
		s.get = _get
		s.execute = _exec_login

		class _CM:
			async def __aenter__(self):
				return s
			async def __aexit__(self, *_exc):
				return False
		return _CM()

	def check(self):
		return None

	def close(self):
		return None


def _make_auth_client(user) -> TestClient:
	a = create_app()
	a.state.settings = get_settings()
	a.state.database = _AuthFakeDB(user)
	return TestClient(a)


# ---------------------------------------------------------------------------
# AC-4: RBAC for /auth/admin/ping
# ---------------------------------------------------------------------------

class TestAC4RoleBasedAccess:
	def test_creator_blocked_from_admin_ping(self):
		a = create_app()
		app = _admin_client(a, _make_user_row(id=uuid.UUID(CREATOR_ID), role="creator"))
		h = _auth_header(CREATOR_ID, "creator")
		r = app.get("/auth/admin/ping", headers=h)
		assert r.status_code == 403

	def test_admin_allowed_on_admin_ping(self):
		a = create_app()
		app = _admin_client(a, _make_user_row(id=uuid.UUID(ADMIN_ID)))
		h = _auth_header(ADMIN_ID, "admin")
		r = app.get("/auth/admin/ping", headers=h)
		assert r.status_code == 200


# ---------------------------------------------------------------------------
# AC-1: create user with temp password → login → must_change_password=true
# ---------------------------------------------------------------------------

class TestAC1TempPasswordFlow:
	def test_create_user_has_must_change_password(self):
		"""POST /users with temp_password → must_change_password=true."""
		a = create_app()
		admin = _make_user_row(id=uuid.UUID(ADMIN_ID))
		app = _admin_client(a, admin)
		h = _auth_header(ADMIN_ID, "admin")
		r = app.post("/users", json={
			"email": "newcreator@test.com",
			"display_name": "New Creator",
			"password": "TempPass123!",
			"role": "creator",
		}, headers=h)
		assert r.status_code == 201
		body = r.json()
		assert body["must_change_password"] is True

	def test_login_returns_must_change_password_true(self):
		a = create_app()
		app = _make_auth_client(_LOGIN_USER)
		r = app.post("/auth/login", json={
			"email": "creator@temp.test",
			"password": "TempPass123!",
		})
		assert r.status_code == 200
		body = r.json()
		assert body.get("must_change_password") is True


# ---------------------------------------------------------------------------
# AC-3: locking last admin → 409
# ---------------------------------------------------------------------------

class TestAC3LastAdminProtection:
	def test_lock_last_admin_returns_409(self):
		"""Only one active admin + trying to lock them → 409."""
		a = create_app()
		only_admin = _make_user_row(id=uuid.UUID(ONLY_ADMIN_ID))
		app = _admin_client(a, only_admin)
		h = _auth_header(ONLY_ADMIN_ID, "admin")
		r = app.post(f"/users/{ONLY_ADMIN_ID}/lock", headers=h)
		assert r.status_code == 409
		assert "admin" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-5: self-lock/demote rejected at service layer
# ---------------------------------------------------------------------------

class TestAC5SelfLockGuard:
	def test_cannot_lock_self(self):
		a = create_app()
		admin = _make_user_row(id=uuid.UUID(ADMIN_ID), must_change_password=False)
		app = _admin_client(a, admin)
		h = _auth_header(ADMIN_ID, "admin")
		r = app.post(f"/users/{ADMIN_ID}/lock", headers=h)
		# service raises 409, API maps to 409
		assert r.status_code == 409

	def test_cannot_demote_self(self):
		a = create_app()
		admin = _make_user_row(id=uuid.UUID(ADMIN_ID), must_change_password=False)
		app = _admin_client(a, admin)
		h = _auth_header(ADMIN_ID, "admin")
		r = app.patch(f"/users/{ADMIN_ID}", json={"role": "creator"}, headers=h)
		assert r.status_code == 409


# ---------------------------------------------------------------------------
# AC-4: creator cannot access /users list
# ---------------------------------------------------------------------------

class TestAC4CreatorBlockedFromUsersAPI:
	def test_creator_get_users_returns_403(self):
		a = create_app()
		app = _admin_client(a, _make_user_row(id=uuid.UUID(CREATOR_ID), role="creator"))
		h = _auth_header(CREATOR_ID, "creator")
		r = app.get("/users", headers=h)
		assert r.status_code == 403
