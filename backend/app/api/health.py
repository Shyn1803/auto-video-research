"""Unauthenticated operational health endpoint."""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

router = APIRouter(tags=["operations"])


class HealthResponse(BaseModel):
    """Public service health contract."""

    status: Literal["ok", "degraded"]
    version: str
    db: Literal["ok", "unavailable"]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse | JSONResponse:
    """Report API and database readiness without exposing connection details."""

    try:
        await request.app.state.database.check()
    except Exception:
        payload = HealthResponse(
            status="degraded", version=request.app.state.settings.app_version, db="unavailable"
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return HealthResponse(status="ok", version=request.app.state.settings.app_version, db="ok")
