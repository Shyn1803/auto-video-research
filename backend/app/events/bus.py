"""In-process async publish/subscribe event bus.

Shape matches the future NATS publisher (AR-5) so that Phase 2 swap is a
one-line import change — call-sites never touch the concrete implementation.
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
    """Fan-out *payload* to every subscriber currently listening on *subject*.

    Fire-and-forget: a slow subscriber that can't keep up gets dropped rather
    than blocking the publisher (no persistence — restart loses in-flight events
    by design per the task Scope Out).
    """

    async with _lock:
        queues = list(_subscribers.get(subject, []))

    if not queues:
        return

    logger.debug("publish %s → %d subscriber(s)", subject, len(queues))
    # put_nowait keeps the publisher non-blocking; subscribers that fall behind
    # get their items dropped with a log warning rather than stalling the bus.
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("subscriber queue full on %s — dropping event", subject)


def subscribe(subject: str) -> AsyncIterator[Any]:
    """Yield events published to *subject* until the consumer is cancelled.

    A matching ``aiter.close()`` (or task cancellation) removes this consumer
    from the subscriber set automatically via the generator's ``finally`` block.
    """

    queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=64)
    loop = asyncio.get_running_loop()

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
                    pass  # already removed

    return _reader()


async def drain() -> None:
    """Drop all subscribers — useful in tests to guarantee a clean slate."""

    async with _lock:
        _subscribers.clear()
