"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.admin.api_keys import router as admin_api_keys_router
from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and dispose infrastructure shared by request handlers."""

    settings: Settings = get_settings()
    app.state.settings = settings
    app.state.database = Database(settings.database_url)
    try:
        yield
    finally:
        await app.state.database.close()


def create_app() -> FastAPI:
    """Build the AVR API application."""

    app = FastAPI(title="AVR API", version=get_settings().app_version, lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(health_router)
    return app


app = create_app()
