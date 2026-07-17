"""Postgres checkpointer wiring for the LangGraph pipeline (Task 4-1 Step 2).

No adapter/module here reads os.environ directly -- the connection string
flows through the existing ``Settings`` object (rules/configuration-env.md).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _psycopg_dsn(settings: Settings) -> str:
    """langgraph-checkpoint-postgres speaks psycopg (v3), this app's
    SQLAlchemy layer speaks asyncpg -- both read the *same* ``database_url``
    setting, just normalized to the driver-less ``postgresql://`` scheme."""
    url = settings.database_url
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


@asynccontextmanager
async def get_checkpointer(
    settings: Settings | None = None,
) -> AsyncIterator[AsyncPostgresSaver]:
    """Yield a Postgres-backed checkpointer with its tables ensured present.

    One saver per call -- revisit pooling only if measured as a bottleneck
    (rules/architecture.md: "tach theo do dac, khong tach truoc").
    """
    settings = settings or get_settings()
    async with AsyncPostgresSaver.from_conn_string(_psycopg_dsn(settings)) as saver:
        await saver.setup()
        yield saver
