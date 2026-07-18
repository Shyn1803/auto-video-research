"""Task 4-4 Step 6/8 -- claim override endpoint: BR-3 audit + sync recompute,
AC4 (override flips verdict), AC6 (non-owner Creator -> 403).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.claim import Claim
from app.models.project import Project
from app.models.user import User

OWNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_CREATOR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ADMIN_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _auth_header(user_id: str, role: str) -> dict[str, str]:
    secret = get_settings().jwt_secret
    token = create_access_token(subject=user_id, role=role, secret=secret)
    return {"Authorization": f"Bearer {token}"}


def _make_user(uid, role):
    u = MagicMock()
    u.id = uid
    u.email = f"{uid}@test.com"
    u.password_hash = hash_password("x")
    u.role = role
    u.is_active = True
    return u


class FakeSession:
    def __init__(self, users: dict, project: Project, claims: dict):
        self.users = users
        self.project = project
        self.claims = claims
        self.committed = False

    async def get(self, model, pk):
        if model is User:
            return self.users.get(str(pk))
        if model is Project:
            return self.project if str(self.project.id) == str(pk) else None
        if model is Claim:
            return self.claims.get(str(pk))
        return None

    async def execute(self, stmt):
        r = MagicMock()
        r.scalars.return_value.all.return_value = list(self.claims.values())
        return r

    def add(self, obj):
        pass

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


class FakeDatabase:
    def __init__(self, session):
        self._session = session

    def session(self):
        class _CM:
            def __init__(self, s):
                self._s = s

            async def __aenter__(self):
                return self._s

            async def __aexit__(self, *exc):
                return False

        return _CM(self._session)

    async def close(self):
        pass


@pytest.fixture
def project():
    p = MagicMock(spec=Project)
    p.id = uuid.uuid4()
    p.owner_id = OWNER_ID
    return p


@pytest.fixture
def claim(project):
    c = MagicMock(spec=Claim)
    c.id = uuid.uuid4()
    c.project_id = project.id
    c.claim_text = "Released on January 15 2026"
    c.claim_type = "release_date"
    c.verdict = "FAIL"
    c.evidence = [{"source_id": "s1", "quote": "q"}]
    c.overridden_by = None
    c.overridden_at = None
    c.override_reason = None
    return c


def _client(project, claims_by_id, requesting_user_role_map):
    app = create_app()
    app.state.settings = get_settings()
    users = {str(uid): _make_user(uid, role) for uid, role in requesting_user_role_map.items()}
    session = FakeSession(users, project, claims_by_id)
    app.state.database = FakeDatabase(session)
    return TestClient(app), session


def test_ac4_owner_override_flips_verdict_and_recomputes(project, claim):
    client, session = _client(project, {str(claim.id): claim}, {OWNER_ID: "creator"})
    h = _auth_header(str(OWNER_ID), "creator")

    resp = client.post(
        f"/projects/{project.id}/claims/{claim.id}/override",
        headers=h,
        json={"verdict": "PASS", "reason": "Confirmed manually with official source"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["claim"]["verdict"] == "PASS"
    assert body["overall_verdict"] == "PASS"
    assert body["affected_claims"] == [str(claim.id)]
    assert claim.overridden_by == str(OWNER_ID)
    assert claim.override_reason == "Confirmed manually with official source"
    assert claim.overridden_at is not None
    assert session.committed is True


def test_ac6_non_owner_creator_gets_403(project, claim):
    client, session = _client(
        project, {str(claim.id): claim}, {OTHER_CREATOR_ID: "creator"}
    )
    h = _auth_header(str(OTHER_CREATOR_ID), "creator")

    resp = client.post(
        f"/projects/{project.id}/claims/{claim.id}/override",
        headers=h,
        json={"verdict": "PASS", "reason": "x"},
    )
    assert resp.status_code == 403


def test_admin_can_override_even_when_not_owner(project, claim):
    client, session = _client(project, {str(claim.id): claim}, {ADMIN_ID: "admin"})
    h = _auth_header(str(ADMIN_ID), "admin")

    resp = client.post(
        f"/projects/{project.id}/claims/{claim.id}/override",
        headers=h,
        json={"verdict": "WARN", "reason": "downgrade after review"},
    )
    assert resp.status_code == 200


def test_invalid_verdict_value_is_400(project, claim):
    client, session = _client(project, {str(claim.id): claim}, {OWNER_ID: "creator"})
    h = _auth_header(str(OWNER_ID), "creator")

    resp = client.post(
        f"/projects/{project.id}/claims/{claim.id}/override",
        headers=h,
        json={"verdict": "MAYBE", "reason": "x"},
    )
    assert resp.status_code == 400
