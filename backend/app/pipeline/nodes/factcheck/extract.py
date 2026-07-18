"""Claim extraction -- Task 4-4 Step 3.

Calls `factcheck.extract_claims` (4-2, get_active_prompt -- never
hardcoded). Excluding subjective opinions (BR-6) is the prompt's own job
("Bo qua y kien chu quan", docs/specs/prompts.md #3) -- this module trusts
the LLM's filtered output and only guards claim_type against the closed
set so a malformed/hallucinated type never reaches the DB CHECK constraint
as a 500 instead of a clean fallback.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.claim import CLAIM_TYPES
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.factcheck.extract")

_EXTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string"},
                    "claim_type": {"type": "string", "enum": list(CLAIM_TYPES)},
                },
                "required": ["claim_text", "claim_type"],
            },
        }
    },
    "required": ["claims"],
}


async def extract_claims(
    session: Any,
    router: Any,
    script_or_summary: str,
    topic: str,
    *,
    correlation_id: str = "",
) -> list[dict[str, str]]:
    """Extract verifiable claims from *script_or_summary* (BR-6)."""
    prompt_version = await get_active_prompt(session, "factcheck.extract_claims")
    if prompt_version is None:
        raise RuntimeError("factcheck.extract_claims prompt is not seeded/active")

    prompt_text = render(
        prompt_version.template,
        {"script_or_summary": script_or_summary, "topic": topic},
    )

    result = await router.call(
        "llm",
        "call_structured",
        tier="strong",
        args=(prompt_text, _EXTRACT_SCHEMA),
        correlation_id=correlation_id,
    )

    claims: list[dict[str, str]] = []
    for raw in result.get("claims", []):
        claim_text = (raw.get("claim_text") or "").strip()
        if not claim_text:
            continue
        claim_type = raw.get("claim_type")
        if claim_type not in CLAIM_TYPES:
            claim_type = "other"
        claims.append({"claim_text": claim_text, "claim_type": claim_type})

    return claims
