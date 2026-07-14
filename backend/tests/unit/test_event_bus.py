"""Step-1 contract: in-process async event bus."""

from __future__ import annotations

import asyncio

import pytest

from app.events import bus as bus_mod
from app.events.bus import drain, publish, subscribe


@pytest.mark.asyncio
async def test_single_subscriber_receives_published_event() -> None:
    await drain()
    received: list = []

    async def consumer() -> None:
        async for event in subscribe("test.subject"):
            received.append(event)
            break

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0)
    await publish("test.subject", {"value": 42})
    await asyncio.wait_for(task, timeout=2.0)
    assert received == [{"value": 42}]


@pytest.mark.asyncio
async def test_no_subscriber_does_not_error() -> None:
    await drain()
    await publish("empty.subject", {"data": True})


@pytest.mark.asyncio
async def test_multiple_subscribers_each_get_event() -> None:
    await drain()
    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()

    async def pipe(q: asyncio.Queue) -> None:
        async for event in subscribe("multi.subject"):
            q.put_nowait(event)
            break

    t1 = asyncio.create_task(pipe(q1))
    t2 = asyncio.create_task(pipe(q2))
    await asyncio.sleep(0)
    await publish("multi.subject", {"id": "x"})
    await asyncio.wait_for(t1, timeout=2.0)
    await asyncio.wait_for(t2, timeout=2.0)
    assert q1.get_nowait() == {"id": "x"}
    assert q2.get_nowait() == {"id": "x"}


@pytest.mark.asyncio
async def test_cancelled_subscriber_is_removed() -> None:
    await drain()
    it = aiter(subscribe("cleanup.subject"))
    it.aclose()  # type: ignore[attr-defined]
    await publish("cleanup.subject", {"ok": True})


@pytest.mark.asyncio
async def test_full_queue_does_not_block_publisher() -> None:
    await drain()
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    for _ in range(64):
        await q.put({"i": 0})

    async def slow() -> AsyncIterator:
        async for event in subscribe("block.subject"):
            yield event

    it = aiter(slow())
    await publish("block.subject", {"overflow": True})
    await asyncio.sleep(0)  # would hang if publish blocked
    it.aclose()  # type: ignore[attr-defined]
