"""Script node -- Task 4-5 Step 4 (`script.generate`, docs/specs/prompts.md §6).

Calls the seeded `script.generate` prompt (4-2), then applies the
deterministic post-checks from `validators.py` (number-set subset,
voice_over symbol-leak, title-length, WARN-claim disclosure) -- per
"Decisions already locked" in the task file, a number-set mismatch is
never a hard block: retry the LLM call once, then flag a warning and
move on (a human decides from there).
"""

from __future__ import annotations

import logging
from typing import Any

from app.pipeline.nodes.write.validators import (
    check_number_subset,
    check_voice_over_symbol_leak,
    check_warn_claim_disclosure,
    enforce_title_length,
)
from app.schemas.step_version import ContentWarning, ScriptContent
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.write.script")

_SCRIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "voice_over": {"type": "string"},
        "estimated_duration_s": {"type": "integer"},
    },
    "required": ["title", "description", "tags", "voice_over", "estimated_duration_s"],
}


def _outline_text(outline: dict[str, Any]) -> str:
    return " ".join(str(v) for v in outline.values() if v)


async def _call_script_llm(
    router: Any, prompt_text: str, *, correlation_id: str
) -> dict[str, Any]:
    return await router.call(
        "llm",
        "call_structured",
        tier="strong",
        args=(prompt_text, _SCRIPT_SCHEMA),
        correlation_id=correlation_id,
    )


async def generate_script(
    session: Any,
    router: Any,
    *,
    topic: str,
    outline: dict[str, Any],
    outline_version: int | None,
    target_duration_s: int,
    warn_claims: list[dict[str, str]] | None = None,
    correlation_id: str = "",
) -> dict[str, Any]:
    """Generate the script from an approved outline. Returns a
    `ScriptContent`-shaped dict (`app/schemas/step_version.py`), ready to
    persist as a `step_versions` row with `step="script"`.

    `outline_version` becomes `content.source_outline_version` -- the
    cross-step lineage pointer AC5 needs (see step_version.py docstring
    for why this can't just reuse `StepVersion.parent_version`).
    """
    prompt_version = await get_active_prompt(session, "script.generate")
    if prompt_version is None:
        raise RuntimeError("script.generate prompt is not seeded/active")

    outline_txt = _outline_text(outline)
    prompt_text = render(
        prompt_version.template,
        {
            "topic": topic,
            "outline_json": outline_txt,
            "target_duration_s": target_duration_s,
        },
    )

    result = await _call_script_llm(router, prompt_text, correlation_id=correlation_id)

    number_check = check_number_subset(outline_txt, result.get("voice_over", ""))
    if not number_check.ok:
        logger.warning(
            "number-set mismatch on first attempt, retrying once: missing=%s "
            "(correlation_id=%s)",
            sorted(number_check.missing), correlation_id,
        )
        result = await _call_script_llm(router, prompt_text, correlation_id=correlation_id)
        number_check = check_number_subset(outline_txt, result.get("voice_over", ""))

    warnings: list[ContentWarning] = []
    if not number_check.ok:
        # Decisions already locked: never hard-block -- flag and continue.
        warnings.append(
            ContentWarning(
                type="number_set_mismatch",
                detail=(
                    "script missing outline number(s) after 1 retry: "
                    f"{sorted(number_check.missing)}"
                ),
            )
        )

    voice_over = result.get("voice_over", "")
    symbol_warning = check_voice_over_symbol_leak(voice_over)
    if symbol_warning is not None:
        warnings.append(symbol_warning)

    title_result = enforce_title_length(result.get("title", ""))
    if title_result.warning is not None:
        warnings.append(title_result.warning)

    if warn_claims:
        warnings.extend(check_warn_claim_disclosure(voice_over, warn_claims))

    content = ScriptContent.model_validate(
        {
            "title": title_result.title,
            "description": result.get("description", ""),
            "tags": result.get("tags", []),
            "voice_over": voice_over,
            "estimated_duration_s": result.get("estimated_duration_s", 0),
            "source_outline_version": outline_version,
            "warnings": [w.model_dump() for w in warnings],
        }
    )
    return content.model_dump(mode="json")
