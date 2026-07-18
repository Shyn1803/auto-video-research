"""Content-hash cache (BR-3) + max-N source cap (BR-4) -- Task 4-3 Step 5.

BR-3: a global cache row (``sources.project_id IS NULL``) means "any project
that has crawled this exact URL within the TTL doesn't need to re-crawl it" --
shared across projects, not per-project (docs/specs/database-schema.md:
"project_id NULL = cache dung chung").
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.models.source import Source

DEFAULT_CACHE_TTL_DAYS = 30
DEFAULT_MAX_SOURCES = 20


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def get_cached_source(
    session: Any, url_hash: str, *, ttl_days: int = DEFAULT_CACHE_TTL_DAYS
) -> Source | None:
    """Return the shared-cache row for *url_hash* if it's still within TTL.

    A hit here means the caller should skip re-crawling the URL (BR-3, AC3).
    """
    cutoff = datetime.now(UTC) - timedelta(days=ttl_days)
    result = await session.execute(
        select(Source).where(
            Source.project_id.is_(None),
            Source.url_hash == url_hash,
            Source.fetched_at >= cutoff,
        )
    )
    return result.scalar_one_or_none()


async def upsert_cache_entry(
    session: Any,
    *,
    url: str,
    url_hash: str,
    title: str | None,
    content: str | None,
    provider: str,
    partial_content: bool,
    trusted: bool,
) -> Source:
    """Insert (or refresh) the shared-cache row for *url_hash*."""
    existing = await get_cached_source(session, url_hash, ttl_days=36500)  # any age, for refresh
    if existing is not None:
        existing.title = title
        existing.content = content
        existing.content_hash = content_hash(content) if content else None
        existing.partial_content = partial_content
        existing.fetched_at = datetime.now(UTC)
        await session.flush()
        return existing

    row = Source(
        project_id=None,
        url=url,
        url_hash=url_hash,
        title=title,
        content=content,
        content_hash=content_hash(content) if content else None,
        provider=provider,
        partial_content=partial_content,
        trusted=trusted,
    )
    session.add(row)
    await session.flush()
    return row


def cap_sources(sources: list[Any], *, max_n: int = DEFAULT_MAX_SOURCES) -> list[Any]:
    """Keep at most *max_n* sources (BR-4) -- caller is responsible for
    passing them in ranked order (best first); this just truncates."""
    return sources[:max_n]
