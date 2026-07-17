"""MockTts — test double for the TTS adapter boundary.

Drop-in replacement for any code path that depends on TTSAdapter:
    from tests.unit.adapters.tts.test_mock_adapter import MockTts

All calls pass through without network IO. Overrides can be pre-staged
in MockTts.override to force specific TTSResult returns for testing
downstream logic.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.adapters.tts.base import ProviderError, TTSAdapter, TTSRequest, TTSResult


# ── test double implementation ────────────────────────────────────────────────


class MockTts(TTSAdapter):
    """Deterministic, zero-IO test double.

    No live calls; records every request for later assertions.
    Override specific cache_keys with a pre-canned TTSResult by writing
    ``MockTts.override[key] = result``.
    """

    name: str = "mock_tts"
    is_paid: bool = False

    calls: ClassVar[list[TTSRequest]] = []
    override: ClassVar[dict[str, TTSResult]] = {}

    def __init__(self, settings=None):
        self._settings = settings
        MockTts.calls = []
        # NOTE: do NOT reset MockTts.override here -- callers stage an override
        # (MockTts.override[key] = result) *before* constructing the adapter;
        # wiping it in __init__ silently defeated the whole override mechanism.

    async def available(self) -> bool:
        return True

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        MockTts.calls.append(request)
        key = request.cache_key(self.name)
        if key in MockTts.override:
            return MockTts.override[key]
        return TTSResult(
            audio_bytes=b"MOCK_MP3",
            duration_ms=1000,
            word_timestamps=[{"word": "mock", "start": 0.0, "end": 1.0}],
            cache_key=key,
        )


# ── unit tests for MockTts itself ─────────────────────────────────────────────


class TestMockTts:
    """MockTts implements the async TTSAdapter contract (available/synthesize
    are ``async def`` per app.adapters.tts.base.TTSAdapter, matching the real
    edge_tts adapter) -- so every call here must be awaited, same as router.py
    does against any real adapter."""

    @pytest.mark.asyncio
    async def test_returns_deterministic_result(self):
        adapter = MockTts()
        req = TTSRequest(text="abc", voice_id="x", speed=1.0)
        r1 = await adapter.synthesize(req)
        r2 = await adapter.synthesize(req)
        assert r1.audio_bytes == r2.audio_bytes
        assert r1.cache_key == r2.cache_key

    @pytest.mark.asyncio
    async def test_records_calls(self):
        adapter = MockTts()
        r1 = await adapter.synthesize(TTSRequest(text="h1", voice_id="v", speed=1.0))
        r2 = await adapter.synthesize(TTSRequest(text="h2", voice_id="v", speed=1.0))
        assert len(MockTts.calls) == 2
        assert MockTts.calls[0].text == "h1"
        assert MockTts.calls[1].text == "h2"
        assert r1.cache_key != r2.cache_key

    @pytest.mark.asyncio
    async def test_override_replace_result(self):
        # Overrides are keyed by the *real* content-addressed cache_key (per
        # the class docstring), not an arbitrary label -- compute it the same
        # way synthesize() does before staging the override.
        req = TTSRequest(text="override_key", voice_id="v", speed=1.0)
        real_key = req.cache_key(MockTts.name)
        custom = TTSResult(
            audio_bytes=b"CUSTOM",
            duration_ms=500,
            word_timestamps=[],
            cache_key=real_key,
        )
        MockTts.override = {real_key: custom}
        adapter = MockTts()
        result = await adapter.synthesize(req)
        assert result.audio_bytes == b"CUSTOM"
        assert result.duration_ms == 500
        MockTts.override = {}

    @pytest.mark.asyncio
    async def test_available_true(self):
        assert await MockTts().available() is True

    def test_registers_as_free(self):
        assert MockTts.is_paid is False
        assert MockTts.name == "mock_tts"

    @pytest.mark.asyncio
    async def test_different_requests_get_different_keys(self):
        adapter = MockTts()
        r1 = await adapter.synthesize(TTSRequest(text="a", voice_id="v", speed=1.0))
        r2 = await adapter.synthesize(TTSRequest(text="b", voice_id="v", speed=1.0))
        assert r1.cache_key != r2.cache_key
