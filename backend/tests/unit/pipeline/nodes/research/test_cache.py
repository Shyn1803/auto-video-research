"""Task 4-3 Step 5 -- content-hash cache (BR-3, AC3) + max-N cap (BR-4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.source import Source
from app.pipeline.nodes.research.cache import (
    cap_sources,
    content_hash,
    get_cached_source,
    upsert_cache_entry,
)


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, rows: list[Source] | None = None):
        self.rows = rows or []
        self.added: list = []
        self.flush_count = 0

    async def execute(self, stmt):
        params = stmt.compile().params
        wanted_hash = params.get("url_hash_1", params.get("url_hash"))
        cutoff = params.get("fetched_at_1", params.get("fetched_at"))
        for row in self.rows:
            if row.project_id is not None:
                continue
            if row.url_hash != wanted_hash:
                continue
            if cutoff is not None and row.fetched_at < cutoff:
                continue
            return _Result(row)
        return _Result(None)

    def add(self, obj):
        self.added.append(obj)
        self.rows.append(obj)

    async def flush(self):
        self.flush_count += 1


def test_content_hash_is_stable_sha256():
    h1 = content_hash("hello world")
    h2 = content_hash("hello world")
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    session = FakeSession()
    result = await get_cached_source(session, "abc123")
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_within_ttl():
    row = Source(
        project_id=None, url="https://x.com/a", url_hash="abc123",
        provider="rss", fetched_at=datetime.now(UTC) - timedelta(days=5),
    )
    session = FakeSession([row])
    result = await get_cached_source(session, "abc123", ttl_days=30)
    assert result is row


@pytest.mark.asyncio
async def test_cache_miss_when_stale_past_ttl():
    """AC3 boundary: a URL crawled 40 days ago is stale for a 30-day TTL --
    must re-crawl, not silently serve ancient content."""
    row = Source(
        project_id=None, url="https://x.com/a", url_hash="abc123",
        provider="rss", fetched_at=datetime.now(UTC) - timedelta(days=40),
    )
    session = FakeSession([row])
    result = await get_cached_source(session, "abc123", ttl_days=30)
    assert result is None


@pytest.mark.asyncio
async def test_upsert_creates_new_row_when_absent():
    session = FakeSession()
    row = await upsert_cache_entry(
        session, url="https://x.com/a", url_hash="h1", title="T",
        content="some content here", provider="rss", partial_content=False,
        trusted=True,
    )
    assert row.project_id is None
    assert row.content_hash == content_hash("some content here")
    assert session.flush_count == 1


@pytest.mark.asyncio
async def test_upsert_refreshes_existing_row_not_duplicate():
    existing = Source(
        project_id=None, url="https://x.com/a", url_hash="h1",
        provider="rss", fetched_at=datetime.now(UTC) - timedelta(days=29),
        content="old content",
    )
    session = FakeSession([existing])
    row = await upsert_cache_entry(
        session, url="https://x.com/a", url_hash="h1", title="New title",
        content="new content", provider="rss", partial_content=False, trusted=True,
    )
    assert row is existing
    assert row.title == "New title"
    assert len(session.rows) == 1  # no duplicate row


def test_cap_sources_truncates_to_max_n():
    sources = list(range(30))
    capped = cap_sources(sources, max_n=20)
    assert len(capped) == 20
    assert capped == list(range(20))


def test_cap_sources_noop_when_under_limit():
    sources = list(range(5))
    assert cap_sources(sources, max_n=20) == sources
