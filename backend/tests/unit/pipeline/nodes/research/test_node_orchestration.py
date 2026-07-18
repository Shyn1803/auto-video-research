"""Task 4-3 Step 7 -- node orchestration: BR-1 fault tolerance + SSE (AC2, AC4, AC6)."""

from __future__ import annotations

import pytest

from app.adapters.base import ProviderError, ProviderSettings, SearchAdapter
from app.adapters.registry import register_search
from app.events import bus as bus_mod
from app.pipeline.nodes.research.node import collect_sources, run_connector


@register_search("fake_ok_a")
class _FakeOkA(SearchAdapter):
    name = "fake_ok_a"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        return [{"title": "Result A", "url": "https://a.com/1", "snippet": ""}]


@register_search("fake_ok_b")
class _FakeOkB(SearchAdapter):
    name = "fake_ok_b"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        return [{"title": "Result B", "url": "https://b.com/1", "snippet": ""}]


@register_search("fake_timeout")
class _FakeTimeout(SearchAdapter):
    name = "fake_timeout"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        raise ProviderError("HN khong truy cap duoc (timeout)", retryable=True)


@register_search("fake_always_fails")
class _FakeAlwaysFails(SearchAdapter):
    name = "fake_always_fails"
    is_paid = False

    async def available(self) -> bool:
        return True

    async def search(self, query, *, max_results=10, language="vi"):
        raise ProviderError("connector broken", retryable=True)


@pytest.fixture(autouse=True)
async def _drain_bus():
    await bus_mod.drain()
    yield


@pytest.mark.asyncio
async def test_run_connector_returns_results_on_success():
    name, results, err = await run_connector("fake_ok_a", "topic")
    assert err is None
    assert results[0]["provider"] == "fake_ok_a"


@pytest.mark.asyncio
async def test_run_connector_returns_error_string_on_failure_never_raises():
    name, results, err = await run_connector("fake_timeout", "topic")
    assert results is None
    assert "khong truy cap duoc" in err


@pytest.mark.asyncio
async def test_run_connector_unknown_name_is_a_soft_error():
    name, results, err = await run_connector("does_not_exist", "topic")
    assert results is None
    assert "not registered" in err


@pytest.mark.asyncio
async def test_ac2_one_connector_timeout_others_succeed():
    """AC2/BR-1: mock HN timeout -> run completes, error recorded, other
    sources present."""
    sources, errors = await collect_sources(
        "topic", connector_names=["fake_ok_a", "fake_timeout", "fake_ok_b"]
    )
    assert len(sources) == 2
    assert "fake_timeout" in errors
    assert "khong truy cap duoc" in errors["fake_timeout"]


@pytest.mark.asyncio
async def test_ac4_every_connector_fails_raises_retryable():
    with pytest.raises(ProviderError) as exc_info:
        await collect_sources(
            "topic", connector_names=["fake_timeout", "fake_always_fails"]
        )
    assert exc_info.value.retryable is True
    assert "khong thu thap duoc nguon" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ac6_sse_progress_names_actual_connector():
    events: list[dict] = []

    async def _collector():
        async for evt in bus_mod.subscribe("step.progress"):
            events.append(evt)
            if len(events) >= 2:
                break

    import asyncio

    task = asyncio.create_task(_collector())
    await asyncio.sleep(0.01)  # let the subscriber attach before publishing
    await collect_sources(
        "topic", connector_names=["fake_ok_a", "fake_ok_b"],
        project_id="p1", run_id="r1",
    )
    await asyncio.wait_for(task, timeout=1)

    messages = [e["payload"]["message"] for e in events]
    assert any("fake_ok_a" in m for m in messages)
    assert any("fake_ok_b" in m for m in messages)
