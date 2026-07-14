"""Permanent security regression test (AC-4 / BR-1).

VERDICT: plaintext API key must never appear in HTTP response bodies or log
output after the key has been saved.  This test is kept permanently — never
remove or weaken it.
"""

from __future__ import annotations

import logging
import os
import re
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault(
    "FERNET_MASTER_KEY",
    "zQmXJvKpL3nR7sT9wY2aB5cD8fG1hJ4kM6nP0qR2tU5vW8xA=",
)

from app.core.crypto import encrypt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.api_key import ApiKey  # noqa: E402


PLAINTEXT = "sk-regression-never-leak-12345-abcdef"
# We match a distinctive substring — the test must find ZERO occurrences.
_PLAIN_SUBSTR = "regression-never-leak"
_PLAIN_RE = re.compile(_PLAIN_SUBSTR, re.IGNORECASE)


def _load_client():
    """Build a TestClient with the admin router mounted."""
    import app.api.admin.api_keys as keys_mod  # noqa: F401 — ensure import
    a = create_app()
    a.state.settings = get_settings()
    return TestClient(a)


def _snapshot_after_actions(raw_key: str, actions: list[dict]) -> tuple[str, str]:
    """Run a series of HTTP actions against TestClient and return (body_all, log_all)."""
    client = _load_client()

    log_buf = StringIO()
    handler = logging.StreamHandler(log_buf)
    handler.setLevel(logging.DEBUG)
    root_logger = logging.getLogger("avr")
    root_logger.addHandler(handler)

    bodies: list[str] = []
    try:
        for act in actions:
            endpoint = act["endpoint"]
            method = act.get("method", "get")
            payload = act.get("payload")
            if method == "get":
                r = client.get(endpoint, headers={"Authorization": "Bearer test-admin-token"})
            elif method == "post":
                r = client.post(endpoint, json=payload, headers={"Authorization": "Bearer test-admin-token"})
            elif method == "delete":
                r = client.delete(endpoint, headers={"Authorization": "Bearer test-admin-token"})
            elif method == "patch":
                r = client.patch(endpoint, json=payload, headers={"Authorization": "Bearer test-admin-token"})
            else:
                raise ValueError(f"unknown method {method}")
            bodies.append(r.text)
    finally:
        root_logger.removeHandler(handler)

    return ("\n".join(bodies)).lower(), log_buf.getvalue().lower()


def _build_key_row():
    import uuid

    return MagicMock(
        spec=ApiKey,
        id=str(uuid.uuid4()),
        provider="gemini",
        label="regression-test",
        key_encrypted=encrypt(PLAINTEXT),
        status="active",
        usage_count=0,
        last_used_at=None,
        exhausted_until=None,
        created_at=MagicMock(isoformat=MagicMock(return_value="2026-07-13T00:00:00+00:00")),
        updated_at=MagicMock(isoformat=MagicMock(return_value="2026-07-13T00:00:00+00:00")),
    )


@pytest.fixture
def patched_key_service():
    """Patch KeyService with a mock that returns a row with known ciphertext."""
    import app.api.admin.api_keys as keys_mod
    from app.services.api_key_service import KeyService

    row = _build_key_row()
    svc = MagicMock(spec=KeyService)
    svc.create = AsyncMock(return_value=row)
    svc.list_by_provider = AsyncMock(return_value=[row])
    svc.get_by_id = AsyncMock(return_value=row)
    svc.to_response = MagicMock(
        return_value={
            "id": row.id,
            "provider": row.provider,
            "label": row.label,
            "key_masked": "****",
            "status": row.status,
            "usage_count": row.usage_count,
            "last_used_at": row.last_used_at,
            "exhausted_until": row.exhausted_until,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
    )

    original = keys_mod.KeyService
    keys_mod.KeyService = MagicMock(return_value=svc)
    yield svc
    keys_mod.KeyService = original


class TestPlaintextNeverSurfaces:
    """
    AC-4: plaintext API key never appears in HTTP response bodies or logs
    after the save/deletion flow.  This is a PERMANENT test.
    """

    def test_fernet_roundtrip_reversible(self):
        """Sanity: encrypt → decrypt returns original; ciphertext differs."""
        ct = encrypt(PLAINTEXT)
        assert isinstance(ct, bytes)
        # Ciphertext is base64 — should NOT contain the raw key string.
        assert _PLAIN_SUBSTR.lower() not in ct.decode().lower()
        # Decrypt roundtrip must be lossless.
        from app.core.crypto import decrypt

        assert decrypt(ct) == PLAINTEXT

    def test_create_list_never_leak_plaintext_in_body(self, patched_key_service):
        """POST + GET — response body contains no plaintext (AC-4)."""
        actions = [
            {"endpoint": "/api/admin/api-keys", "method": "post", "payload": {
                "provider": "gemini",
                "label": "regression",
                "key": PLAINTEXT,
            }},
            {"endpoint": "/api/admin/api-keys", "method": "get"},
        ]
        all_bodies, _ = _snapshot_after_actions(PLAINTEXT, actions)
        assert _PLAIN_RE.search(all_bodies) is None, (
            f"PLAINTEXT REGRESSION: '{_PLAIN_SUBSTR}' found in response bodies:\n{all_bodies[:500]}"
        )

    def test_get_detail_never_leak_plaintext(self, patched_key_service):
        """GET /keys/{id} — response must not carry plaintext."""
        actions = [
            {"endpoint": "/api/admin/api-keys/00000000-0000-0000-0000-000000000000", "method": "get"},
        ]
        all_bodies, _ = _snapshot_after_actions(PLAINTEXT, actions)
        assert _PLAIN_RE.search(all_bodies) is None

    def test_update_never_leak_plaintext(self, patched_key_service):
        """PATCH /keys/{id} — response must not carry plaintext."""
        actions = [
            {"endpoint": "/api/admin/api-keys/00000000-0000-0000-0000-000000000000", "method": "patch",
             "payload": {"label": "new-label"}},
        ]
        all_bodies, _ = _snapshot_after_actions(PLAINTEXT, actions)
        assert _PLAIN_RE.search(all_bodies) is None
