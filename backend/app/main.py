"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin.api_keys import router as admin_api_keys_router
from app.api.admin.costs import router as admin_costs_router
from app.api.admin.providers import router as admin_providers_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.runs import router as runs_router
from app.api.scenes import router as scenes_router
from app.api.users import router as users_router
from app.api.versions import router as versions_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.pipeline.checkpoint import get_checkpointer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and dispose infrastructure shared by request handlers."""

    settings: Settings = get_settings()
    app.state.settings = settings
    app.state.database = Database(settings.database_url)

    # Best-effort: a Postgres-backed LangGraph checkpointer lets pipeline
    # runs resume across restarts (Task 4-1 AC2). Unavailable in
    # environments with no Postgres reachable (e.g. this dev sandbox) --
    # degrade to no persistent checkpoint rather than fail app startup,
    # per rules/configuration-env.md's "log why a provider was excluded".
    app.state.checkpointer = None
    checkpointer_cm = None
    try:
        checkpointer_cm = get_checkpointer(settings)
        app.state.checkpointer = await checkpointer_cm.__aenter__()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pipeline checkpointer unavailable at startup: %s", exc)
        checkpointer_cm = None

    try:
        yield
    finally:
        if checkpointer_cm is not None:
            await checkpointer_cm.__aexit__(None, None, None)
        await app.state.database.close()


def create_app() -> FastAPI:
    """Build the AVR API application."""

    app = FastAPI(title="AVR API", version=get_settings().app_version, lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(projects_router)
    app.include_router(versions_router)
    app.include_router(admin_api_keys_router)
    app.include_router(admin_providers_router)
    app.include_router(admin_costs_router)
    app.include_router(runs_router)
    app.include_router(scenes_router)
    return app


app = create_app()
