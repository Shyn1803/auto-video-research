"""Step-2 contract: event envelope schemas + state_machine wiring."""

from __future__ import annotations

import asyncio

import pytest

from app.events import bus as bus_mod
from app.events.schemas import project_status, step_progress
from app.services.state_machine import EDGES, ProjectStateMachine, ProjectStatus, TransitionError


@pytest.mark.asyncio
async def test_project_status_event_publishes_on_bus() -> None:
    """transition() emits project.status event on the bus."""

    await bus_mod.drain()
    sm = ProjectStateMachine(bus=bus_mod)
    received: list = []

    async def _collect() -> None:
        async for event in bus_mod.subscribe("project.status"):
            received.append(event)
            break

    task = asyncio.create_task(_collect())
    await asyncio.sleep(0)

    await sm.transition(
        project_id="proj-1",
        from_state="APPROVED",
        to_state="PRODUCING",
        correlation_id="run-abc",
        actor="system",
        reason="user clicked run",
    )

    await asyncio.wait_for(task, timeout=2.0)
    assert received, "no event received"
    env = received[0]
    assert isinstance(env, dict)
    assert env["event_type"] == "project.status"
    assert env["correlation_id"] == "run-abc"
    assert env["schema_version"] == "1.0.0"
    assert env["payload"]["project_id"] == "proj-1"
    assert env["payload"]["from_state"] == "APPROVED"
    assert env["payload"]["to_state"] == "PRODUCING"
    assert env["payload"]["actor"] == "system"


@pytest.mark.asyncio
async def test_forbidden_edge_raises_transition_error() -> None:
    """FR-17 matrix blocks PUBLISHED -> RESEARCHING."""

    sm = ProjectStateMachine(bus=bus_mod)
    with pytest.raises(TransitionError, match="Invalid transition"):
        await sm.transition(
            project_id="proj-x",
            from_state="PUBLISHED",
            to_state="RESEARCHING",
            correlation_id="run-1",
        )


@pytest.mark.asyncio
async def test_no_bus_means_no_publish() -> None:
    """When bus=None the service validates the edge but emits nothing."""

    await bus_mod.drain()
    sm = ProjectStateMachine(bus=None)
    await sm.transition(
        project_id="proj-x",
        from_state="APPROVED",
        to_state="PRODUCING",
        correlation_id="run-1",
    )
    # no subscribers registered -> drain returns immediately, no error


@pytest.mark.asyncio
async def test_idempotent_same_state_is_noop() -> None:
    """Transitioning to the same state is a silent no-op (BR-5)."""

    await bus_mod.drain()
    sm = ProjectStateMachine(bus=bus_mod)
    received: list = []

    async def _collect() -> None:
        async for event in bus_mod.subscribe("project.status"):
            received.append(event)
            break

    task = asyncio.create_task(_collect())
    await asyncio.sleep(0)

    await sm.transition(
        project_id="proj-x",
        from_state="DRAFT",
        to_state="DRAFT",
        correlation_id="run-1",
    )

    await asyncio.sleep(0.1)
    # No event should be published for an idempotent same-state call
    assert received == []


def test_step_progress_envelope() -> None:
    """step_progress() helper produces the right envelope."""
    env = step_progress(
        project_id="p1",
        run_id="r1",
        step="research",
        pct=45,
        correlation_id="cid",
    )
    assert env.event_type == "step.progress"
    payload = env.payload
    assert isinstance(payload, dict)
    assert payload["project_id"] == "p1"
    assert payload["pct"] == 45


def test_project_status_envelope() -> None:
    """project_status() helper produces the right envelope."""
    env = project_status(
        project_id="p1",
        from_state="DRAFT",
        to_state="RESEARCHING",
        correlation_id="cid",
        actor="system",
    )
    assert env.event_type == "project.status"
    assert env.payload["from_state"] == "DRAFT"


def test_all_statuses_present_in_edges() -> None:
    """Every ProjectStatus member must appear as a key in EDGES."""
    for status in ProjectStatus:
        assert status in EDGES.edges, f"{status} missing from EDGES"
