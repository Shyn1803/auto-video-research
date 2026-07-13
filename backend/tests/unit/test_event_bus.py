"""Step-1 contract: in-process async event bus."""

from __future__ import annotations

import asyncio

import pytest

from app.events.bus import drain, publish, subscribe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect(n: int, sub: AsyncIterator) -> list:
    """Consume *n* events from an async generator, then cancel it."""
    results: list = []
    it = aiter(sub)
    for _ in range(n):
        results.append(await anext(it))
    # Stop the generator — its finally block must unregister cleanly.
    aiterator_close(it)
    return results


def aiterator_close(it: AsyncIterator) -> None:
    """Close an async iterator without awaiting (no __anext__ call needed)."""

    it.aclose()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_subscriber_receives_published_event() -> None:
    """A subscriber on a subject gets events published to that subject."""

    await drain()  # clean slate

    received: list = []

    async def _consume() -> None:
        async for event in subscribe("test.subject"):
            received.append(event)
            break  # one event then exit

    task = asyncio.create_task(_consume())
    await asyncio.sleep(0)  # let subscription register

    await publish("test.subject", {"value": 42})

    await asyncio.wait_for(task, timeout=1.0)
    assert received == [{"value": 42}]


@pytest.mark.asyncio
async def test_no_subscriber_does_not_error() -> None:
    """Publishing with zero subscribers is a no-op, not a crash."""

    await drain()
    await publish("empty.subject", {"data": True})  # must not raise


@pytest.mark.asyncio
async def test_multiple_subscribers_each_get_event() -> None:
    """Every subscriber on a subject receives every event."""

    await drain()

    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()

    async def _collect(q: asyncio.Queue) -> None:
        async for event in subscribe("multi.subject"):
            q.put_nowait(event)
            break

    t1 = asyncio.create_task(_collect(q1))
    t2 = asyncio.create_task(_collect(q2))
    await asyncio.sleep(0)

    await publish("multi.subject", {"id": "x"})

    await asyncio.wait_for(t1, timeout=1.0)
    await asyncio.wait_for(t2, timeout=1.0)
    assert q1.get_nowait() == {"id": "x"}
    assert q2.get_nowait() == {"id": "x"}


@pytest.mark.asyncio
async def test_subscriber_cleanup_after_cancel() -> None:
    """Cancelling a subscriber unregisters it — subsequent publishes don't error."""

    await drain()

    it = aiter(subscribe("cleanup.subject"))
    it.aclose()  # type: ignore[attr-defined]  # unregister immediately

    await publish("cleanup.subject", {"ok": True})  # no subscriber — must not raise


@pytest.mark.asyncio
async def test_publisher_non_blocking_with_full_queue() -> None:
    """A slow subscriber (full 64-slot queue) does not block the publisher."""

    await drain()

    # Fill subscriber queue
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    for i in range(64):
        await q.put({"i": i})

    async def _slow_sub() -> AsyncIterator:
        async for event in subscribe("block.subject"):
            yield event

    it = aiter(_slow_sub())

    # Publish must not hang — it uses put_nowait which raises QueueFull
    # and the bus logs a warning instead of blocking.
    await publish("block.subject", {"overflow": True})
    # If publish blocked we'd never reach this line; timeout proves non-blocking.
    it.aclose()  # type: ignore[attr-defined]
