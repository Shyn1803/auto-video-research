"""One-time-token service for SSE stream authentication (BR-3).

Token: URL-safe 32-byte random string, TTL 60s, single-use.
Stored in-memory in a service-scoped dict — no persistence, restart
clears all outstanding tokens (acceptable: FE fetches a fresh one on
connect).
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

_TOKEN_TTL_SECONDS = 60


@dataclass
class _TokenRecord:
    token: str
    project_id: str
    user_role: str  # "admin" | "viewer" — 1-2 will replace with real User
    used: bool = False
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + _TOKEN_TTL_SECONDS)


class EventTokenService:
    """Issue and redeem one-time tokens for the SSE endpoint."""

    def __init__(self) -> None:
        self._tokens: dict[str, _TokenRecord] = {}
        self._by_project: dict[str, set[str]] = {}

    def issue(self, *, project_id: str, user_role: str) -> str:
        token = secrets.token_urlsafe(32)
        record = _TokenRecord(
            token=token,
            project_id=project_id,
            user_role=user_role,
        )
        self._tokens[token] = record
        self._by_project.setdefault(project_id, set()).add(token)
        return token

    async def consume(self, token: str) -> _TokenRecord | None:
        """Validate and consume — returns the record or None if invalid."""

        await self._prune_expired()
        record = self._tokens.pop(token, None)
        if record is None:
            return None
        if record.used:
            return None
        record.used = True
        proj_tokens = self._by_project.get(record.project_id)
        if proj_tokens is not None:
            proj_tokens.discard(token)
        return record

    async def _prune_expired(self) -> None:
        now = time.time()
        to_remove = [t for t, r in self._tokens.items() if r.expires_at <= now]
        for t in to_remove:
            r = self._tokens.pop(t, None)
            if r is not None:
                self._by_project.get(r.project_id, set()).discard(t)


# Module-level singleton — same instance injected into every request via
# FastAPI's Depends() so FE connections share a consistent token store.
_current: EventTokenService | None = None


def get_event_token_service() -> EventTokenService:
    global _current
    if _current is None:
        _current = EventTokenService()
    return _current
