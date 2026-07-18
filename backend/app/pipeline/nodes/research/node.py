"""Research node orchestration -- Task 4-3 Step 7.

Connectors are complementary sources, not chain-failover alternatives
(unlike LLM/TTS providers) -- BR-1 says "1 connector loi -> skip; run fail
chi khi MOI connector loi", i.e. every configured connector is queried on
every run, not "try the next one only if this one fails". So this module
calls each registered search adapter directly via the registry, not
through ProviderRouter.call() (which implements chain-failover semantics
that don't apply here).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.adapters.base import ProviderError
from app.adapters.registry import get_adapter_class
from app.events.bus import publish
from app.events.schemas import step_progress

logger = logging.getLogger("avr.research.node")

DEFAULT_CONNECTORS: list[str] = ["arxiv", "hn_algolia", "github", "rss", "searxng"]


class ProgressCallback(Protocol):
    async def __call__(self, message: str) -> None: ...


async def _publish_progress(
    project_id: str, run_id: str, message: str, *, pct: int = 0
) -> None:
    try:
        await publish(
            "step.progress",
            step_progress(
                project_id=project_id,
                run_id=run_id,
                step="research",
                pct=pct,
                correlation_id=run_id,
                message=message,
            ).model_dump(),
        )
    except Exception:  # noqa: BLE001 -- event bus is fire-and-forget
        logger.debug("event bus unavailable for step.progress run=%s", run_id)


async def run_connector(
    name: str, query: str, *, max_results: int = 10
) -> tuple[str, list[dict[str, str]] | None, str | None]:
    """Run one connector. Returns (name, results_or_None, error_or_None) --
    never raises, per BR-1 (the caller decides whether to fail the node)."""
    adapter_cls = get_adapter_class("search", name)
    if adapter_cls is None:
        return name, None, f"connector {name!r} not registered"

    adapter = adapter_cls()
    try:
        if not await adapter.available():
            return name, None, f"{name} khong kha dung (thieu cau hinh)"
        results = await adapter.search(query, max_results=max_results)
        for r in results:
            r["provider"] = name
        return name, results, None
    except ProviderError as exc:
        return name, None, str(exc)
    except Exception as exc:  # noqa: BLE001 -- isolate any connector's own bug too
        return name, None, str(exc)


async def collect_sources(
    query: str,
    *,
    connector_names: list[str] | None = None,
    max_results_per_connector: int = 10,
    project_id: str = "",
    run_id: str = "",
) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Run every connector, tolerating individual failures (BR-1, AC2).

    Raises ProviderError(retryable=True) only when *every* connector fails
    (AC4). Emits a step.progress event naming the actual connector being
    read (AC6) before each call.
    """
    names = connector_names if connector_names is not None else DEFAULT_CONNECTORS
    all_results: list[dict[str, str]] = []
    errors: dict[str, str] = {}

    for name in names:
        await _publish_progress(project_id, run_id, f"dang doc {name}")
        conn_name, results, err = await run_connector(
            name, query, max_results=max_results_per_connector
        )
        if err is not None:
            errors[conn_name] = err
            logger.warning("connector %s failed: %s", conn_name, err)
        else:
            all_results.extend(results or [])

    if names and len(errors) == len(names):
        raise ProviderError(
            "khong thu thap duoc nguon (moi connector deu loi): "
            + "; ".join(f"{k}: {v}" for k, v in errors.items()),
            retryable=True,
        )

    return all_results, errors
