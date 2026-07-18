"""Task 4-2 Step 7 / AC3 -- Creator forbidden from admin prompt routes.

Uses the shared admin_client/creator_client fixtures from tests/conftest.py
(same pattern as tests/integration/test_rbac.py) -- RBAC rejects before the
route body ever touches the DB, so the fixtures' narrow fake session is
sufficient here even though it isn't a full Prompt-aware fake.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings

ADMIN_ID = "11111111-1111-1111-1111-111111111111"
CREATOR_ID = "22222222-2222-2222-2222-222222222222"


def _auth_header(user_id: str, role: str) -> dict[str, str]:
    from app.core.security import create_access_token

    secret = get_settings().jwt_secret
    token = create_access_token(subject=user_id, role=role, secret=secret)
    return {"Authorization": f"Bearer {token}"}


class TestAC3PromptAdminRBAC:
    def test_creator_blocked_from_list_prompts(self, creator_client: TestClient) -> None:
        h = _auth_header(CREATOR_ID, "creator")
        r = creator_client.get("/api/admin/prompts", headers=h)
        assert r.status_code == 403

    def test_creator_blocked_from_activate(self, creator_client: TestClient) -> None:
        h = _auth_header(CREATOR_ID, "creator")
        r = creator_client.post(
            "/api/admin/prompts/script.generate/versions/2/activate", headers=h
        )
        assert r.status_code == 403

    def test_creator_blocked_from_create_version(self, creator_client: TestClient) -> None:
        h = _auth_header(CREATOR_ID, "creator")
        r = creator_client.post(
            "/api/admin/prompts/script.generate/versions",
            headers=h,
            json={"template": "hi {{ x }}", "variables": ["x"]},
        )
        assert r.status_code == 403
