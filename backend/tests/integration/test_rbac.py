"""RBAC integration tests — AC-4: creator blocked from admin routes, admin allowed."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings


def _auth_header(user_id: str, role: str) -> dict[str, str]:
    """Build a Bearer token header for a test user."""
    from app.core.security import create_access_token

    secret = get_settings().jwt_secret
    token = create_access_token(subject=user_id, role=role, secret=secret)
    return {"Authorization": f"Bearer {token}"}


ADMIN_ID = "11111111-1111-1111-1111-111111111111"
CREATOR_ID = "22222222-2222-2222-2222-222222222222"


class TestAC4RoleBasedAccessControl:
    """AC-4: A creator hitting /auth/admin/ping gets 403;
    an admin hitting the same endpoint gets 200."""

    def test_creator_blocked_from_admin_route(self, creator_client: TestClient) -> None:
        h = _auth_header(CREATOR_ID, "creator")
        r = creator_client.get("/auth/admin/ping", headers=h)
        assert r.status_code == 403

    def test_admin_allowed_on_admin_route(self, admin_client: TestClient) -> None:
        h = _auth_header(ADMIN_ID, "admin")
        r = admin_client.get("/auth/admin/ping", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["detail"] == "admin endpoint"
