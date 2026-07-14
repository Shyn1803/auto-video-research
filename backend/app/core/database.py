"""Database lifecycle — engine + async session factory for request handlers."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Database:
    """Own the SQLAlchemy async engine and session factory."""

    def __init__(self, database_url: str) -> None:
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._engine: AsyncEngine = create_async_engine(async_url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    async def check(self) -> None:
        """Raise when PostgreSQL cannot answer a lightweight query."""
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Release database resources during API shutdown."""
        await self._engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Auto-commit context manager for request handlers."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
