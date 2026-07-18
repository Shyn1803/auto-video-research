"""Outline node -- Task 4-5 Step 3 (`outline.generate`, docs/specs/prompts.md §5).

Calls the seeded `outline.generate` prompt (4-2, `get_active_prompt` --
never hardcoded) with the already-designed contract: 7 mandatory
narrative sections (hook/introduction/problem/solution/demo/conclusion/
cta) plus one optional/nullable `controversy` section, each expected to
cite `[source_id]`, built only from `claims_passed` (BR-1 filtering
already happened in `context.py` before this module is ever called).
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.step_version import OutlineContent
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.write.outline")

MANDATORY_SECTIONS: tuple[str, ...] = (
    "hook", "introduction", "problem", "solution", "demo", "conclusion", "cta",
)

_OUTLINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "outline": {
            "type": "object",
            "properties": {
                "hook": {"type": "string"},
                "introduction": {"type": "string"},
                "problem": {"type": "string"},
                "controversy": {"type": ["string", "null"]},
                "solution": {"type": "string"},
                "demo": {"type": "string"},
                "conclusion": {"type": "string"},
                "cta": {"type": "string"},
            },
            "required": list(MANDATORY_SECTIONS),
        }
    },
    "required": ["outline"],
}


def sections_missing_source_citation(outline: dict[str, Any]) -> list[str]:
    """Which of the 7 mandatory sections have no `[source_id]`-shaped
    citation (AC1: "Outline 7 phần đủ [source_id]")."""
    missing = []
    for key in MANDATORY_SECTIONS:
        text = outline.get(key) or ""
        if "[" not in text or "]" not in text:
            missing.append(key)
    return missing


def _format_claims_passed(claims_passed: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {c.get('claim_text', '')}" for c in claims_passed)


async def generate_outline(
    session: Any,
    router: Any,
    *,
    topic: str,
    ranked_summaries: str,
    target_duration_s: int,
    claims_passed: list[dict[str, Any]],
    correlation_id: str = "",
) -> dict[str, Any]:
    """Generate the outline. Returns an `OutlineContent`-shaped dict
    (`app/schemas/step_version.py`), ready to persist as a `step_versions`
    row with `step="outline"`.
    """
    prompt_version = await get_active_prompt(session, "outline.generate")
    if prompt_version is None:
        raise RuntimeError("outline.generate prompt is not seeded/active")

    prompt_text = render(
        prompt_version.template,
        {
            "topic": topic,
            "ranked_summaries": ranked_summaries,
            "target_duration_s": target_duration_s,
            "claims_passed": _format_claims_passed(claims_passed),
        },
    )

    result = await router.call(
        "llm",
        "call_structured",
        tier="strong",
        args=(prompt_text, _OUTLINE_SCHEMA),
        correlation_id=correlation_id,
    )

    outline = result.get("outline", {})
    missing = sections_missing_source_citation(outline)
    if missing:
        logger.warning(
            "outline sections missing [source_id] citation: %s (correlation_id=%s)",
            missing, correlation_id,
        )

    content = OutlineContent.model_validate({"outline": outline, "warnings": []})
    return content.model_dump(mode="json")
