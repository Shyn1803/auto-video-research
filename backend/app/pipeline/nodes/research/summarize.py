"""Bounded-parallel summarize -- Task 4-3 Step 6.

Calls the `research.summarize` prompt (tier ``cheap`` per rules/performance.md)
through get_active_prompt (4-2) -- never hardcodes the template (4-2 BR-4's
CI guard would fail this file if it did). A single source's summarize
failure only flags that source (BR-5) -- it never raises out of
``summarize_sources`` and never blocks the whole node.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.research.summarize")

DEFAULT_CONCURRENCY = 4
MIN_SUCCESSFUL_SUMMARIES = 5  # BR-5 quality bar, checked by the caller/AC1

_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary_vi": {"type": "string"},
        "key_facts": {"type": "array", "items": {"type": "string"}},
        "relevance_to_topic": {"type": "number"},
        "published_info": {
            "type": "object",
            "properties": {"date": {"type": ["string", "null"]}, "author": {"type": ["string", "null"]}},
        },
    },
    "required": ["summary_vi", "key_facts", "relevance_to_topic"],
}


class SummarizedSource(TypedDict, total=False):
    url: str
    title: str
    summary_vi: str | None
    key_facts: list[str]
    relevance_to_topic: float | None
    summarize_failed: bool
    summarize_error: str | None


async def summarize_one(
    session: Any,
    router: Any,
    source: dict[str, Any],
    topic: str,
    *,
    correlation_id: str = "",
) -> SummarizedSource:
    """Summarize a single source. Raises on failure -- callers (summarize_sources)
    are responsible for catching and flagging per BR-5, this function itself
    stays a plain "success or raise" unit so it's simple to test in isolation."""
    prompt_version = await get_active_prompt(session, "research.summarize")
    if prompt_version is None:
        raise RuntimeError("research.summarize prompt is not seeded/active")

    prompt_text = render(
        prompt_version.template,
        {
            "topic": topic,
            "article_title": source.get("title", ""),
            "article_content": source.get("content", ""),
            "source_url": source.get("url", ""),
        },
    )

    result = await router.call(
        "llm",
        "call_structured",
        tier="cheap",
        args=(prompt_text, _SUMMARY_SCHEMA),
        correlation_id=correlation_id,
    )

    return SummarizedSource(
        url=source.get("url", ""),
        title=source.get("title", ""),
        summary_vi=result.get("summary_vi"),
        key_facts=result.get("key_facts", []),
        relevance_to_topic=result.get("relevance_to_topic"),
        summarize_failed=False,
        summarize_error=None,
    )


async def summarize_sources(
    session: Any,
    router: Any,
    sources: list[dict[str, Any]],
    topic: str,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    correlation_id: str = "",
) -> list[SummarizedSource]:
    """Summarize *sources* with bounded parallelism.

    A per-source failure never raises out of this function (BR-5) -- the
    failing source comes back flagged ``summarize_failed=True`` instead.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(source: dict[str, Any]) -> SummarizedSource:
        async with semaphore:
            try:
                return await summarize_one(session, router, source, topic, correlation_id=correlation_id)
            except Exception as exc:  # noqa: BLE001 -- BR-5: flag, don't propagate
                logger.warning(
                    "summarize failed for %s: %s", source.get("url", "?"), exc,
                    extra={"correlation_id": correlation_id},
                )
                return SummarizedSource(
                    url=source.get("url", ""),
                    title=source.get("title", ""),
                    summary_vi=None,
                    key_facts=[],
                    relevance_to_topic=None,
                    summarize_failed=True,
                    summarize_error=str(exc),
                )

    return list(await asyncio.gather(*[_bounded(s) for s in sources]))


def count_successful(results: list[SummarizedSource]) -> int:
    return sum(1 for r in results if not r.get("summarize_failed", False))
