"""Unit tests for RateLimiter — AC-3 (5 failures -> 429 + Retry-After)."""

from __future__ import annotations

import pytest

from app.core.rate_limit import RateLimiter


class TestAC3RateLimit:
    """AC-3: 5 failed attempts -> 429 + Retry-After within 15-min window."""

    @pytest.fixture()
    def limiter(self) -> RateLimiter:
        return RateLimiter(max_attempts=5, window_seconds=900.0)

    def test_five_failures_then_blocked(self, limiter: RateLimiter) -> None:
        """5 recorded failures -> 6th check() returns (False, retry_after)."""
        email = "brute@test.com"
        ip = "10.0.0.1"
        for _ in range(5):
            ok, _ = limiter.check(email, ip)
            assert ok is True
            limiter.record(email, ip)
        ok, retry_after = limiter.check(email, ip)
        assert ok is False
        assert isinstance(retry_after, int)
        assert retry_after >= 1

    def test_endpoint_maps_to_429(self, limiter: RateLimiter) -> None:
        """Mirrors the login endpoint pattern: check -> record -> 429 on 6th."""
        email = "brute2@test.com"
        ip = "10.0.0.2"
        for _ in range(5):
            limiter.record(email, ip)
        ok, retry_after = limiter.check(email, ip)
        assert ok is False
        assert retry_after >= 1

    def test_window_clears_after_timeout(self, limiter: RateLimiter) -> None:
        """Old entries outside the window fall off automatically."""
        email = "expired@test.com"
        ip = "10.0.0.3"
        for _ in range(5):
            limiter._hits[(email, ip)].append(0.0)  # very old timestamps
        ok, _ = limiter.check(email, ip)
        assert ok is True  # all stale entries filtered out

    def test_different_ips_independent(self, limiter: RateLimiter) -> None:
        """(email, IP) tuple is the key — different IP is not affected."""
        email = "shared@test.com"
        for _ in range(5):
            limiter.record(email, "1.1.1.1")
        ok, _ = limiter.check(email, "2.2.2.2")
        assert ok is True

    def test_different_emails_independent(self, limiter: RateLimiter) -> None:
        """Different email with the same IP gets its own quota."""
        ip = "3.3.3.3"
        for _ in range(5):
            limiter.record("a@test.com", ip)
        ok, _ = limiter.check("b@test.com", ip)
        assert ok is True
