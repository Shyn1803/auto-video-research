"""verify_claim -- Task 4-4 Step 4 (BR-1, BR-2, BR-4).

Applies the gates AFTER the LLM's own PASS/WARN/FAIL read (per
docs/specs/prompts.md #4's own PASS/WARN/FAIL rule) because BR-1/BR-2 are
counting/data-quality rules the LLM has no way to enforce reliably from
inside a single prompt call -- they're deterministic post-checks, not
"AI judgment", matching this project's "AI never decides structure/rules
alone" ethos applied to fact-checking too.
"""

from __future__ import annotations

import logging
from typing import Any

from app.pipeline.nodes.factcheck.evidence import gather_evidence
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.factcheck.verify")

ORPHAN_MESSAGE = "khong tim thay nguon xac nhan"

_VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "WARN", "FAIL"]},
        "supporting_source_ids": {"type": "array", "items": {"type": "string"}},
        "contradicting_source_ids": {"type": "array", "items": {"type": "string"}},
        "explanation_vi": {"type": "string"},
    },
    "required": ["verdict", "explanation_vi"],
}


def count_independent_supporting_domains(
    evidence: list[dict[str, Any]], supporting_ids: list[str]
) -> int:
    """BR-1: PASS needs >=2 independent (different root domain) supporting
    sources -- 2 articles on the same blog count as 1."""
    supporting = {e["root_domain"] for e in evidence if e["source_id"] in supporting_ids}
    return len(supporting)


def has_partial_content_support(
    evidence: list[dict[str, Any]], supporting_ids: list[str]
) -> bool:
    """BR-2: any supporting evidence from a partial_content source caps the
    verdict at WARN -- a title+abstract snippet isn't enough for PASS."""
    return any(
        e.get("partial_content") for e in evidence if e["source_id"] in supporting_ids
    )


async def verify_claim(
    session: Any,
    router: Any,
    claim_text: str,
    sources: list[dict[str, Any]],
    *,
    correlation_id: str = "",
) -> dict[str, Any]:
    """Verify one claim against *sources*. Returns
    {verdict, supporting_source_ids, contradicting_source_ids, explanation_vi, evidence}.
    """
    evidence = gather_evidence(claim_text, sources)

    if not evidence:
        # BR-4: no LLM call needed -- there's nothing to verify against.
        return {
            "verdict": "WARN",
            "supporting_source_ids": [],
            "contradicting_source_ids": [],
            "explanation_vi": ORPHAN_MESSAGE,
            "evidence": [],
        }

    prompt_version = await get_active_prompt(session, "factcheck.verify_claim")
    if prompt_version is None:
        raise RuntimeError("factcheck.verify_claim prompt is not seeded/active")

    prompt_text = render(
        prompt_version.template,
        {
            "claim_text": claim_text,
            "evidence_json": [
                {
                    "source_id": e["source_id"],
                    "quote": e["quote"],
                    "source_trusted": e["source_trusted"],
                }
                for e in evidence
            ],
        },
    )

    result = await router.call(
        "llm",
        "call_structured",
        tier="strong",
        args=(prompt_text, _VERIFY_SCHEMA),
        correlation_id=correlation_id,
    )

    verdict = result.get("verdict", "WARN")
    supporting_ids = result.get("supporting_source_ids", [])
    contradicting_ids = result.get("contradicting_source_ids", [])
    explanation = result.get("explanation_vi", "")

    if verdict == "PASS":
        independent_domains = count_independent_supporting_domains(evidence, supporting_ids)
        if independent_domains < 2:
            # BR-1
            verdict = "WARN"
        elif has_partial_content_support(evidence, supporting_ids):
            # BR-2
            verdict = "WARN"

    return {
        "verdict": verdict,
        "supporting_source_ids": supporting_ids,
        "contradicting_source_ids": contradicting_ids,
        "explanation_vi": explanation,
        "evidence": evidence,
    }
