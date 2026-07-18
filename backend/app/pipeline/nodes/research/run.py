"""run_research -- the full Task 4-3 pipeline composed: connectors -> crawl ->
dedupe -> cache -> cap -> summarize + ai_summary (Step 7/8, AC1 + task 5-10).

Kept as a plain function taking session/router as explicit arguments (not
a LangGraph node signature) so it's testable in isolation with fakes --
``research_node`` (node.py's LangGraph-facing wrapper, wired into
app/pipeline/graph.py) is the thin adapter that opens the real DB session
and ProviderRouter and calls this.

AI summary (task 5-10): after summarizing sources, a cheap-tier LLM call
generates a 2-sentence summary cached in the research step_version content
under key ``ai_summary``. Failure is non-fatal -- None is stored instead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.adapters.base import ProviderError
from app.pipeline.nodes.research.cache import (
    cap_sources,
    get_cached_source,
    upsert_cache_entry,
)
from app.pipeline.nodes.research.crawl import crawl_url
from app.pipeline.nodes.research.dedupe import SourceCandidate, dedupe_by_url_hash, url_hash
from app.pipeline.nodes.research.node import DEFAULT_CONNECTORS, collect_sources
from app.pipeline.nodes.research.summarize import count_successful, summarize_sources
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.research.run")

DEFAULT_MAX_SOURCES = 20

_AI_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ai_summary": {"type": "string"},
    },
    "required": ["ai_summary"],
}


def _build_ranked_summaries(summarized: list[dict[str, Any]]) -> str:
    """Format summarized sources into a compact text block for the LLM prompt."""
    parts: list[str] = []
    for i, s in enumerate(summarized, 1):
        if s.get("summarize_failed"):
            continue
        title = s.get("title", "(không tiêu đề)")
        summary_vi = s.get("summary_vi", "")
        facts = s.get("key_facts", [])
        parts.append(
            f"Nguồn {i}: {title}\n"
            f"  Tóm tắt: {summary_vi}\n"
            + (f"  Facts: {'; '.join(facts)}\n" if facts else "")
        )
    return "\n".join(parts) if parts else "(không có nguồn tóm tắt thành công)"


async def _generate_ai_summary(
    session: Any, router: Any, topic: str, summarized: list[dict[str, Any]], *, correlation_id: str = ""
) -> str | None:
    """Generate a 2-sentence AI summary for the research result (task 5-10).

    Calls the ``research.ai_summary`` prompt (cheap tier). Failure is
    non-fatal: returns None so the caller stores None in step_version content.
    """
    prompt_version = await get_active_prompt(session, "research.ai_summary")
    if prompt_version is None:
        logger.debug("research.ai_summary prompt not seeded -- skipping AI summary")
        return None

    ranked_text = _build_ranked_summaries(summarized)
    prompt_text = render(
        prompt_version.template,
        {"topic": topic, "ranked_summaries": ranked_text},
    )

    try:
        result = await router.call(
            "llm",
            "call_structured",
            tier="cheap",
            args=(prompt_text, _AI_SUMMARY_SCHEMA),
            correlation_id=correlation_id,
        )
        raw = result.get("ai_summary", "")
        # Sanitize: strip markdown wrappers the LLM may add
        cleaned = raw.strip().strip('"').strip("'")
        return cleaned if cleaned else None
    except Exception as exc:  # noqa: BLE001 -- non-fatal, log and continue
        logger.warning(
            "AI summary generation failed: %s", exc, extra={"correlation_id": correlation_id}
        )
        return None


async def run_research(
    session: Any,
    router: Any,
    topic: str,
    *,
    connector_names: list[str] | None = None,
    max_results_per_connector: int = 10,
    max_sources: int = DEFAULT_MAX_SOURCES,
    project_id: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    """Run the full research pipeline for *topic*. Returns the payload that
    becomes ``PipelineState.research``.

    Raises ProviderError(retryable=True) only if every connector fails
    (AC4) -- everything after that point (crawl/dedupe/cache/summarize)
    degrades gracefully per-item rather than raising.
    """
    hits, connector_errors = await collect_sources(
        topic,
        connector_names=connector_names or DEFAULT_CONNECTORS,
        max_results_per_connector=max_results_per_connector,
        project_id=project_id,
        run_id=run_id,
    )

    # Crawl each hit's URL for full content -- exact url_hash duplicates
    # across connectors are collapsed *before* crawling so we never fetch
    # the same URL twice in one run (cheap win on top of the cache).
    seen_hashes: set[str] = set()
    unique_hits: list[dict[str, Any]] = []
    for hit in hits:
        h = url_hash(hit["url"])
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        unique_hits.append(hit)

    candidates: list[SourceCandidate] = []
    crawl_errors: dict[str, str] = {}
    contents: dict[str, dict[str, Any]] = {}

    for hit in unique_hits:
        h = url_hash(hit["url"])
        cached = await get_cached_source(session, h)
        if cached is not None:
            title, content, partial = cached.title, cached.content, cached.partial_content
        else:
            try:
                result = await crawl_url(hit["url"])
            except ProviderError as exc:
                crawl_errors[hit["url"]] = str(exc)
                continue
            title = result.title or hit.get("title")
            content = result.content
            partial = result.partial_content
            await upsert_cache_entry(
                session,
                url=hit["url"],
                url_hash=h,
                title=title,
                content=content,
                provider=hit.get("provider", "unknown"),
                partial_content=partial,
                trusted=hit.get("provider") == "rss",  # rss = curated trusted-vendor list
            )

        contents[h] = {
            "url": hit["url"],
            "title": title,
            "content": content,
            "partial_content": partial,
            "provider": hit.get("provider", "unknown"),
        }
        candidates.append(
            SourceCandidate(id=h, url=hit["url"], url_hash=h, trusted=hit.get("provider") == "rss")
        )

    # Dedupe already-collapsed-by-hash candidates is a no-op here (unique_hits
    # is already unique per hash) -- kept as an explicit call so a future
    # embedding-similarity pass (real BGE-M3 vectors) drops in without
    # restructuring this function; today it only exercises the url_hash path.
    deduped = dedupe_by_url_hash(candidates)
    ranked = cap_sources(deduped, max_n=max_sources)

    ranked_sources = [contents[c.url_hash] for c in ranked]

    summarized = (
        await summarize_sources(
            session, router, ranked_sources, topic, correlation_id=run_id
        )
        if ranked_sources
        else []
    )
    # summarize_sources only returns the LLM-facing fields -- merge back
    # partial_content/provider (crawl-time facts, not summarizer output) by
    # URL so the caller sees the full picture in one place.
    by_url = {s["url"]: s for s in ranked_sources}
    for item in summarized:
        extra = by_url.get(item.get("url"))
        if extra is not None:
            item["partial_content"] = extra["partial_content"]
            item["provider"] = extra["provider"]

    successful = count_successful(summarized)

    # ── task 5-10: generate 2-sentence AI summary (cheap tier, non-fatal) ──
    ai_summary = await _generate_ai_summary(
        session, router, topic, summarized, correlation_id=run_id
    )

    return {
        "topic": topic,
        "sources": summarized,
        "connector_errors": connector_errors,
        "crawl_errors": crawl_errors,
        "total_sources": len(ranked_sources),
        "summarized_ok": successful,
        "ai_summary": ai_summary,
    }
