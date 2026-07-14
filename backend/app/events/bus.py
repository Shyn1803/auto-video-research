"""In-process async publish/subscribe event bus.

Shape matches the future NATS publisher (AR-5) so that Phase 2 swap is a
one-line import change -- call-sites never touch the concrete implementation.

Fire-and-forget: no persistence, restart loses in-flight events by design
(task Scope Out).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
_lock = asyncio.Lock()


async def publish(subject: str, payload: Any) -> None:
    """Fan *payload* out to every subscriber currently listening on *subject*.

    Slow subscribers are dropped with a warning rather than stalling the
    publisher -- ``maxsize=64`` keeps memory bounded and ``put_nowait`` is
    non-blocking by design.
    """

    async with _lock:
        queues = list(_subscribers.get(subject, []))

    if not queues:
        return

    logger.debug("publish %s -> %d subscriber(s)", subject, len(queues))
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning(
                "bus subscriber queue full on %s - dropping event", subject
            )


def subscribe(subject: str) -> AsyncIterator[Any]:
    """Yield events published to *subject* until the caller cancels.

    Unsubscribes automatically when the generator closes (task cancellation,
    aclose() call, or break-out by the caller).
    """

    queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=64)

    async def _reader() -> AsyncIterator[Any]:
        async with _lock:
            _subscribers[subject].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with _lock:
                try:
                    _subscribers[subject].remove(queue)
                except ValueError:
                    pass

    return _reader()


async def drain() -> None:
    """Drop every subscriber -- for tests that need a guaranteed-clean slate."""

    async with _lock:
        _subscribers.clear()
