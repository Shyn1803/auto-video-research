"""Task 4-1 Step 2 -- checkpointer DSN handling (unit-level, no live Postgres)."""

from __future__ import annotations

from app.core.config import Settings
from app.pipeline.checkpoint import _psycopg_dsn


def test_asyncpg_url_normalized_to_plain_postgresql():
    settings = Settings(database_url="postgresql+asyncpg://app:app@localhost:5432/app")
    assert _psycopg_dsn(settings) == "postgresql://app:app@localhost:5432/app"


def test_plain_postgresql_url_left_untouched():
    settings = Settings(database_url="postgresql://app:app@localhost:5432/app")
    assert _psycopg_dsn(settings) == "postgresql://app:app@localhost:5432/app"
