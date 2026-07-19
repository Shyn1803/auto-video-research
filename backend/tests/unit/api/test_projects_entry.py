"""Step 2 - script_text validation on POST /projects (BR-2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import CREATOR_USER

# In-memory fake DB
_PROJECTS = {}
_STEP_VERSIONS = []
_SESSION_USER = CREATOR_USER

class _FakeProject:
    __tablename__ = "projects"
    def __init__(self, **kw):
        self.id = kw.get("id") or uuid.uuid4()
        self.owner_id = kw.get("owner_id", uuid.UUID("22222222-2222-2222-2222-222222222222"))
        self.name = kw.get("name", "Test")
        self.topic = kw.get("topic", "t")
        self.mode = kw.get("mode", "interactive")
        self.status = kw.get("status", "DRAFT")
        self.entry_point = kw.get("entry_point", "research")
        self.language = kw.get("language", "vi")
        self.formats = kw.get("formats", ["vertical_1080x1920"])
        self.voice_id = kw.get("voice_id")
        self.voice_gender = kw.get("voice_gender", "female")
        self.cloned_from = kw.get("cloned_from")
        self.archived_at = kw.get("archived_at")
        self.created_at = kw.get("created_at") or datetime.now(UTC).replace(tzinfo=None)
        self.updated_at = kw.get("updated_at") or datetime.now(UTC).replace(tzinfo=None)

class _FakeStepVersion:
    __tablename__ = "step_versions"
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class FakeSession:
    async def get(self, model, pk):
        name = getattr(model, "__name__", "")
        if "User" in name:
            return _SESSION_USER
        if "Project" in name:
            return _PROJECTS.get(pk)
        return None

    async def execute(self, stmt):
        from app.models.step_version import StepVersion
        r = MagicMock()
        q = str(stmt).lower()
        if "step_versions" in q and "max" in q:
            pids = list(_PROJECTS.keys())
            svs = [sv for sv in _STEP_VERSIONS if sv.project_id in pids]
            r.scalar_one_or_none.return_value = max((sv.version for sv in svs), default=0)
        elif "step_versions" in q:
            pids = list(_PROJECTS.keys())
            cnt = sum(1 for sv in _STEP_VERSIONS if sv.project_id in pids)
            r.scalar.return_value = cnt
            r.scalar_one_or_none.return_value = cnt
        elif "refresh" in q and "update" in q:
            r.rowcount = 1
            r.scalar_one_or_none.return_value = None
        else:
            r.scalar_one_or_none.return_value = _SESSION_USER
            r.scalars.return_value.all.return_value = [_SESSION_USER]
        return r

    async def flush(self): pass
    async def commit(self): pass
    async def close(self): pass
    async def rollback(self): pass

    def add(self, obj):
        tname = getattr(type(obj), "__tablename__", "")
        if tname == "projects":
            _PROJECTS[obj.id] = obj
        elif tname == "step_versions":
            _STEP_VERSIONS.append(obj)

_SINGLETON_SESSION = FakeSession()

class _CM:
    async def __aenter__(self):
        return _SINGLETON_SESSION
    async def __aexit__(self, *exc):
        return False

class FakeDatabase:
    def session(self):
        return _CM()
    async def check(self): pass
    async def close(self): pass


def _auth_header(user_id: str, role: str = "creator") -> dict[str, str]:
    from app.core.security import create_access_token
    secret = get_settings().jwt_secret
    token = create_access_token(subject=user_id, role=role, secret=secret)
    return {"Authorization": f"Bearer {token}"}

SCRIPT_VALID_LEN = 200

def _script(n: int) -> str:
    return "x" * n


# ---------------------------------------------------------------------------
# Api_app fixture -- patch ProjectOut.from_orm
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_app():
    from app.main import create_app
    from app.schemas.project import ProjectOut

    a = create_app()
    a.state.settings = get_settings()
    a.state.database = FakeDatabase()

    _orig = ProjectOut.from_orm
    _NOW = datetime.now(UTC).replace(tzinfo=None)

    @classmethod
    def _fake(cls, project, step_count=0, step_progress=None):
        ep = getattr(project, 'entry_point', None) or 'research'
        pid = getattr(project, "id", None) or uuid.uuid4()
        return cls(
            id=pid,
            name=getattr(project, 'name', None) or 'Test',
            topic=getattr(project, 'topic', None) or 't',
            mode=getattr(project, 'mode', None) or 'interactive',
            status=getattr(project, 'status', None) or 'DRAFT',
            entry_point=ep,
            language=getattr(project, 'language', None) or 'vi',
            formats=getattr(project, 'formats', None) or ['vertical_1080x1920'],
            voice_id=getattr(project, 'voice_id', None),
            voice_gender=getattr(project, 'voice_gender', None) or 'female',
            cloned_from=getattr(project, 'cloned_from', None),
            archived_at=getattr(project, 'archived_at', None),
            created_at=getattr(project, 'created_at', None) or _NOW,
            updated_at=getattr(project, 'updated_at', None) or _NOW,
            step_count=step_count,
            next_action={'label': 'Tiep tuc chinh sua', 'href': '/edit'},
        )

    ProjectOut.from_orm = _fake
    yield a
    ProjectOut.from_orm = _orig


@pytest.fixture()
def api_client(api_app):
    return TestClient(api_app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_with_valid_script(api_client):
    h = _auth_header(str(CREATOR_USER.id))
    body = {
        'name': 'Project Script Entry',
        'topic': 'AI news',
        'mode': 'interactive',
        'script_text': _script(SCRIPT_VALID_LEN)
    }
    r = api_client.post('/projects', json=body, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()['entry_point'] == 'script'


def test_create_with_short_script(api_client):
    h = _auth_header(str(CREATOR_USER.id))
    body = {
        'name': 'Project Short Script',
        'topic': 'AI news',
        'mode': 'interactive',
        'script_text': _script(50),
    }
    r = api_client.post('/projects', json=body, headers=h)
    assert r.status_code == 400, r.text
    assert '100' in r.json()['detail']


def test_create_with_long_script(api_client):
    h = _auth_header(str(CREATOR_USER.id))
    body = {
        'name': 'Project Long Script',
        'topic': 'AI news',
        'mode': 'interactive',
        'script_text': _script(3500),
    }
    r = api_client.post('/projects', json=body, headers=h)
    assert r.status_code == 400, r.text
    assert '3000' in r.json()['detail']


def test_create_without_script(api_client):
    h = _auth_header(str(CREATOR_USER.id))
    body = {
        'name': 'Project No Script',
        'topic': 'AI news',
        'mode': 'interactive',
    }
    r = api_client.post('/projects', json=body, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()['entry_point'] == 'research'
