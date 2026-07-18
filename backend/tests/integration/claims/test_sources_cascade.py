"""Task 4-4 Step 7 -- disabling a source cascades a synchronous claim
verdict recompute (BR-5, AC3)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.claim import Claim
from app.models.project import Project
from app.models.source import Source
from app.models.user import User

OWNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _auth_header(user_id: str, role: str) -> dict[str, str]:
    secret = get_settings().jwt_secret
    token = create_access_token(subject=user_id, role=role, secret=secret)
    return {"Authorization": f"Bearer {token}"}


def _make_user(uid, role):
    u = MagicMock()
    u.id = uid
    u.password_hash = hash_password("x")
    u.role = role
    u.is_active = True
    return u


class FakeSession:
    def __init__(self, user, project, source, claims):
        self.user = user
        self.project = project
        self.source = source
        self.claims = claims

    async def get(self, model, pk):
        if model is User:
            return self.user
        if model is Project:
            return self.project if str(self.project.id) == str(pk) else None
        if model is Source:
            return self.source if str(self.source.id) == str(pk) else None
        return None

    async def execute(self, _stmt):
        r = MagicMock()
        r.scalars.return_value.all.return_value = list(self.claims.values())
        return r

    def add(self, obj):
        pass

    async def flush(self):
        pass

    async def commit(self):
        pass

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


def test_ac3_disable_sole_evidence_source_downgrades_pass_claim_to_warn():
    project = MagicMock(spec=Project)
    project.id = uuid.uuid4()
    project.owner_id = OWNER_ID

    source = MagicMock(spec=Source)
    source.id = uuid.uuid4()
    source.project_id = project.id
    source.disabled = False

    claim = MagicMock(spec=Claim)
    claim.id = uuid.uuid4()
    claim.project_id = project.id
    claim.verdict = "PASS"
    claim.evidence = [
        {"source_id": str(source.id), "root_domain": "onlysource.com", "quote": "q"}
    ]

    user = _make_user(OWNER_ID, "creator")
    session = FakeSession(user, project, source, {str(claim.id): claim})

    app = create_app()
    app.state.settings = get_settings()
    app.state.database = FakeDatabase(session)
    client = TestClient(app)
    h = _auth_header(str(OWNER_ID), "creator")

    resp = client.patch(
        f"/projects/{project.id}/sources/{source.id}",
        headers=h,
        json={"disabled": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["disabled"] is True
    assert str(claim.id) in body["affected_claims"]
    assert claim.verdict == "WARN"
