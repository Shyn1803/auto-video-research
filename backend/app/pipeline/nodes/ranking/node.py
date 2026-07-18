"""Ranking node -- Task 4-4 Step 2.

Calls `ranking.score` (from 4-2, get_active_prompt -- never hardcoded, per
4-2's CI guard) with configurable weights (never hardcoded in the template
itself, per rules/performance.md) -- weights come from Settings
(app/core/config.py), which is the one place they're allowed to live.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.ranking.node")

_RANKING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "score": {"type": "number"},
                    "reason_vi": {"type": "string"},
                },
                "required": ["source_id", "score"],
            },
        }
    },
    "required": ["rankings"],
}


async def rank_sources(
    session: Any,
    router: Any,
    sources: list[dict[str, Any]],
    topic: str,
    *,
    weight_recency: float,
    weight_relevance: float,
    weight_trust: float,
    weight_confirm: float,
    correlation_id: str = "",
) -> list[dict[str, Any]]:
    """Score+reason every source via the ranking.score prompt.

    Returns *sources* (same objects) with ``score``/``reason`` set;
    sources the LLM didn't return a ranking for keep ``score=None``.
    """
    prompt_version = await get_active_prompt(session, "ranking.score")
    if prompt_version is None:
        raise RuntimeError("ranking.score prompt is not seeded/active")

    sources_json = json.dumps(
        [
            {
                "id": s.get("id") or s.get("source_id") or s.get("url"),
                "title": s.get("title", ""),
                "summary_vi": s.get("summary_vi", ""),
                "published_at": s.get("published_at", ""),
                "provider": s.get("provider", ""),
                "trusted": s.get("trusted", False),
            }
            for s in sources
        ],
        ensure_ascii=False,
    )

    prompt_text = render(
        prompt_version.template,
        {
            "topic": topic,
            "today": datetime.now(UTC).date().isoformat(),
            "w_recency": weight_recency,
            "w_relevance": weight_relevance,
            "w_trust": weight_trust,
            "w_confirm": weight_confirm,
            "sources_json": sources_json,
        },
    )

    result = await router.call(
        "llm",
        "call_structured",
        tier="cheap",
        args=(prompt_text, _RANKING_SCHEMA),
        correlation_id=correlation_id,
    )

    scores_by_id = {
        r["source_id"]: r for r in result.get("rankings", []) if r.get("source_id")
    }

    for source in sources:
        source_id = source.get("id") or source.get("source_id") or source.get("url")
        ranking = scores_by_id.get(source_id)
        if ranking is not None:
            source["score"] = ranking.get("score")
            source["reason"] = ranking.get("reason_vi")
        else:
            source.setdefault("score", None)
            source.setdefault("reason", None)

    return sources
