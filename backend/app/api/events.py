"""SSE endpoint — one-time token issuance + real-time event stream.

BR-2: stream filter by role — creator sees only their own project; admin sees all.
BR-3: one-time token TTL 60s, single use.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.events.bus import subscribe
from app.models.project import Project
from app.models.user import User
from app.services.event_token_service import (
    EventTokenService,
    get_event_token_service,
)

router = APIRouter()


@router.post("/events/token", status_code=status.HTTP_201_CREATED)
async def issue_event_token(
    project_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    token_service: EventTokenService = Depends(get_event_token_service),
) -> dict[str, object]:
    """Issue a one-time bearer token for an SSE stream connection.

    - creator: token scoped to *project_id*; stream filters events for that project only.
    - admin: token scoped to *project_id*; admin receives all events.

    BR-3: TTL 60s, single use — the FE fetches a fresh token for every new EventSource
    connect (reconnect triggers re-issue; handled by Step 5 hook).
    """
    # BR-2: creator must own the project to get a scoped token
    if user.role != "admin":
        async with request.app.state.database.session() as session:
            proj = await session.get(Project, project_id)
        if proj is None or str(proj.owner_id) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not authorized for this project",
            )

    token = token_service.issue(project_id=project_id, user_role=user.role)
    return {"token": token, "expires_in": 60}


@router.get("/events/stream")
async def stream_events(
    token: str,
    token_service: EventTokenService = Depends(get_event_token_service),
) -> StreamingResponse:
    """HTTP SSE endpoint streaming ``project.status`` events.

    Business rules
    - BR-3: token is consumed on the very first byte of this response; reconnecting
            the same EventSource (browser retry with same URL) or replay with the
            same token → 401.
    - BR-2: creator gets only events whose payload[\"project_id\"] matches the
            project_id embedded in the token; admin gets every project's events.
    - BR-1: every message validates against the EventEnvelope schema_version=1.0.0.

    FE reconnect (BR-4): the Step-5 hook closes the stale EventSource, calls
    ``GET /runs/{run_id}`` once to resync the current state, then re-issues a
    fresh ``POST /events/token`` and opens a *new* ``GET /events/stream?token=…``.
    """
    record = await token_service.consume(token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        )

    event_subject = "project.status"

    async def _generate() -> AsyncGenerator[str, None]:
        """Yield SSE ``data:`` lines with BR-2 project filter applied."""
        try:
            async for event in subscribe(event_subject):
                payload = event.get("payload", {})
                # BR-2 — restrict creator to their own project only
                if record.user_role != "admin":
                    if payload.get("project_id") != record.project_id:
                        continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            # Stream terminated (client disconnect or server shutdown); let uvicorn
            # clean up the generator silently instead of propagating the exception.
            return

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx response buffering for SSE
        },
    )
