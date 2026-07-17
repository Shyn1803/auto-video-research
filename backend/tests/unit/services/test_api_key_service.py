"""Unit tests for KeyService — Fernet roundtrip, CRUD, masking, exhaustion."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# FERNET_MASTER_KEY must be set before any import of app.core.crypto
os.environ.setdefault(
    "FERNET_MASTER_KEY",
    "zQmXJvKpL3nR7sT9wY2aB5cD8fG1hJ4kM6nP0qR2tU5vW8xA=",
)

from app.core.crypto import decrypt, encrypt, mask  # noqa: E402
from app.models.api_key import ApiKey  # noqa: E402
from app.services.api_key_service import KeyService  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────


def _make_row(**overrides):
    """Build a MagicMock ApiKey row with Fernet-encrypted key."""
    import uuid

    defaults = dict(
        id=str(uuid.uuid4()),
        provider="gemini",
        label="test-label",
        key_encrypted=encrypt("sk-test-key-12345"),
        status="active",
        usage_count=0,
        last_used_at=None,
        exhausted_until=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return MagicMock(spec=ApiKey, **defaults)


def _session_cm(session_mock):
    """Wrap a mock session as an async context manager."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ── Fernet roundtrip (AC-4 baseline) ──────────────────────────────────────


class TestFernetRoundtrip:
    def test_encrypt_then_decrypt(self):
        raw = "sk-demo-key-abcdef123456"
        ct = encrypt(raw)
        assert isinstance(ct, bytes)
        assert decrypt(ct) == raw

    def test_ciphertext_differs_from_plaintext(self):
        raw = "my-secret-key"
        ct = encrypt(raw)
        assert raw.encode() not in ct

    def test_mask_short_key(self):
        assert mask("abcd") == "abcd"
        assert mask("abc") == "abc****"

    def test_mask_normal_key(self):
        assert mask("AIzaSyD1234567890abcdef") == "AIzaSyD1...cdef"

    def test_mask_empty(self):
        assert mask("") == ""


# ── get_plaintext ────────────────────────────────────────────────────────


class TestGetPlaintext:

    def test_valid_ciphertext_decrypts(self):
        raw = "sk-valid-key"
        row = _make_row(key_encrypted=encrypt(raw))
        svc = KeyService(None)
        assert svc.get_plaintext(row) == raw

    def test_bad_ciphertext_raises(self):
        row = _make_row(key_encrypted=b"not-valid!!!")
        svc = KeyService(None)
        with pytest.raises(RuntimeError, match="stored ciphertext is invalid"):
            svc.get_plaintext(row)


# ── create / get_by_id / delete ──────────────────────────────────────────


class TestCRUD:

    @pytest.mark.asyncio
    async def test_create_key(self):
        session = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = MagicMock()
        session.add = MagicMock()

        svc = KeyService(lambda: _session_cm(session))
        row = await svc.create(
            provider="gemini",
            label="my-label",
            plaintext_key="sk-new-key-abc",
        )
        assert row.provider == "gemini"
        assert row.label == "my-label"
        # key_encrypted must be bytes (ciphertext), not plaintext
        assert row.key_encrypted != b"sk-new-key-abc"
        session.add.assert_called_once()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_strips_whitespace(self):
        session = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = MagicMock()
        session.add = MagicMock()

        svc = KeyService(lambda: _session_cm(session))
        row = await svc.create(
            provider="  gemini  ",
            label="  my label  ",
            plaintext_key="sk-key-000",
        )
        assert row.provider == "gemini"
        assert row.label == "my label"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        row = _make_row()
        session = MagicMock()
        session.get = MagicMock(return_value=row)

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.get_by_id(row.id)
        assert result is row

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        session = MagicMock()
        session.get = MagicMock(return_value=None)

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.get_by_id("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        row = _make_row()
        session = MagicMock()
        session.get = MagicMock(return_value=row)
        session.delete = MagicMock()
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.delete(row.id)
        assert result is not None
        session.delete.assert_called_once_with(row)
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_missing_returns_none(self):
        session = MagicMock()
        session.get = MagicMock(return_value=None)

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.delete("nonexistent")
        assert result is None
        session.delete.assert_not_called()


# ── Masking / response (AC-4 security) ───────────────────────────────────


class TestMaskedResponses:

    def test_list_response_never_contains_plaintext(self):
        """AC-4: to_response list view — plaintext never appears."""
        raw = "sk-very-secret-api-key-12345"
        row = _make_row(key_encrypted=encrypt(raw))
        svc = KeyService(None)
        data = svc.to_response(row)  # no plaintext arg → list view
        assert data["key_masked"] == "****"
        assert raw not in str(data)

    def test_detail_response_masks_key(self):
        """Detail view: masked form only, never raw key."""
        raw = "sk-detail-test-key-999"
        row = _make_row(key_encrypted=encrypt(raw))
        svc = KeyService(None)
        data = svc.to_response(row, plaintext=raw)
        assert raw not in data["key_masked"]
        assert "****" in data["key_masked"] or "..." in data["key_masked"]


# ── Exhaustion / re-activation (AC-1) ────────────────────────────────────


class TestExhaustion:

    @pytest.mark.asyncio
    async def test_mark_exhausted_sets_fields(self):
        row = _make_row(status="active", exhausted_until=None)
        session = MagicMock()
        session.get = MagicMock(return_value=row)
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        until = datetime.now(UTC) + timedelta(hours=12)
        await svc.mark_exhausted(row.id, until=until)

        assert row.status == "exhausted"
        assert row.exhausted_until == until
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_mark_exhausted_defaults_to_midnight_utc(self):
        row = _make_row(status="active", exhausted_until=None)
        session = MagicMock()
        session.get = MagicMock(return_value=row)
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        await svc.mark_exhausted(row.id)

        assert row.status == "exhausted"
        assert row.exhausted_until is not None
        assert row.exhausted_until.hour == 0
        assert row.exhausted_until.minute == 0

    @pytest.mark.asyncio
    async def test_reactivate_expired(self):
        now = datetime.now(UTC)
        exhausted_row = _make_row(
            status="exhausted",
            exhausted_until=now - timedelta(hours=1),
        )
        session = MagicMock()

        async def _execute(stmt, *a, **kw):
            r = MagicMock()
            r.scalars.return_value.all.return_value = [exhausted_row]
            r.scalar_one_or_none.return_value = None
            return r

        session.execute = _execute
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        count = await svc.reactivate_expired()

        assert exhausted_row.status == "active"
        assert exhausted_row.exhausted_until is None


# ── track_usage ──────────────────────────────────────────────────────────


class TestTrackUsage:

    @pytest.mark.asyncio
    async def test_increments_counter(self):
        row = _make_row(usage_count=5)
        session = MagicMock()
        session.get = MagicMock(return_value=row)
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        count = await svc.track_usage(row.id)

        assert count >= 5
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_track_usage_sets_last_used_at(self):
        row = _make_row(last_used_at=None)
        session = MagicMock()
        session.get = MagicMock(return_value=row)
        session.commit = AsyncMock()

        svc = KeyService(lambda: _session_cm(session))
        svc.track_usage(row.id)

        assert row.last_used_at is not None


# ── list_by_provider ─────────────────────────────────────────────────────


class TestListByProvider:

    @pytest.mark.asyncio
    async def test_list_all(self):
        rows = [_make_row(provider="gemini"), _make_row(provider="gemini")]
        session = MagicMock()

        async def _execute(stmt, *a, **kw):
            r = MagicMock()
            r.scalars.return_value.all.return_value = rows
            return r

        session.execute = _execute

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.list_by_provider()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_provider(self):
        gemini_rows = [_make_row(provider="gemini")]
        groq_rows = [_make_row(provider="groq")]
        call_count = [0]

        async def _execute(stmt, *a, **kw):
            r = MagicMock()
            q = str(stmt)
            if "gemini" in q:
                r.scalars.return_value.all.return_value = gemini_rows
            else:
                r.scalars.return_value.all.return_value = groq_rows
            return r

        session = MagicMock()
        session.execute = _execute

        svc = KeyService(lambda: _session_cm(session))
        result = await svc.list_by_provider("gemini")
        assert all(r.provider == "gemini" for r in result)
