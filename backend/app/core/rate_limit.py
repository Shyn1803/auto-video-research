"""Simple in-memory rate limiter keyed on email+IP."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """5 failed attempts per (email, IP) per 15 minutes."""

    def __init__(self, max_attempts: int = 5, window_seconds: float = 900.0) -> None:
        self._max = max_attempts
        self._window = window_seconds
        self._hits: dict[tuple[str, str], list[float]] = defaultdict(list)

    def check(self, email: str, ip: str) -> tuple[bool, int | None]:
        key = (email.lower(), ip)
        now = time.monotonic()
        cutoff = now - self._window
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        count = len(self._hits[key])
        if count >= self._max:
            retry_after = int(self._hits[key][0] + self._window - now) + 1
            return False, max(retry_after, 1)
        return True, None

    def record(self, email: str, ip: str) -> None:
        key = (email.lower(), ip)
        self._hits[key].append(time.monotonic())


limiter = RateLimiter()
