"""Database lifecycle — engine + declarative Base for models."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Database:
    """Own the SQLAlchemy async engine used by the API process."""

    def __init__(self, database_url: str) -> None:
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._engine: AsyncEngine = create_async_engine(async_url, pool_pre_ping=True)

    async def check(self) -> None:
        """Raise when PostgreSQL cannot answer a lightweight query."""

        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Release database resources during API shutdown."""

        await self._engine.dispose()
