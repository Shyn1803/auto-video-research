"""FactCheck node orchestration -- Task 4-4 Step 5.

Overall verdict per docs/specs/database-schema.md's own rule (§2.4 note):
FAIL if any claim FAILs; WARN if any claim WARNs; PASS only if every claim
PASSes. On FAIL, the project moves to NEED_REVIEW and a notify event fires
-- Scope Out for this task says the real notify channel (Telegram/email)
is task 7-4's job; here it's logged only, but the call site (7-4) is a
drop-in replacement of ``_notify`` below, not a redesign.
"""

from __future__ import annotations

import logging
from typing import Any

from app.pipeline.nodes.factcheck.extract import extract_claims
from app.pipeline.nodes.factcheck.verify import verify_claim

logger = logging.getLogger("avr.factcheck.node")

_VERDICT_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2, "PENDING": 1}


def compute_overall_verdict(verdicts: list[str]) -> str:
    """FAIL if any FAIL; WARN if any WARN; PASS if all PASS (empty -> PASS,
    vacuously true -- no claims means nothing failed verification)."""
    if not verdicts:
        return "PASS"
    if "FAIL" in verdicts:
        return "FAIL"
    if any(v != "PASS" for v in verdicts):
        return "WARN"
    return "PASS"


def _notify(project_id: str, overall_verdict: str, failed_claims: list[dict[str, Any]]) -> None:
    """Scope Out: real channel (Telegram/email) is task 7-4 -- log only here."""
    logger.warning(
        "factcheck notify: project=%s overall=%s failed_claims=%d",
        project_id, overall_verdict, len(failed_claims),
    )


async def run_factcheck(
    session: Any,
    router: Any,
    project: Any,
    script_or_summary: str,
    sources: list[dict[str, Any]],
    topic: str,
    *,
    actor: str = "system",
    correlation_id: str = "",
) -> dict[str, Any]:
    """Extract claims, verify each, compute overall verdict, gate on FAIL.

    Returns {claims: [...], overall_verdict}. Caller (research_node-style
    LangGraph wrapper) is responsible for persisting Claim rows -- this
    function stays DB-model-agnostic so it's testable with plain dicts.
    """
    from app.services.state_machine import ProjectStateMachine

    raw_claims = await extract_claims(session, router, script_or_summary, topic, correlation_id=correlation_id)

    verified: list[dict[str, Any]] = []
    for raw in raw_claims:
        result = await verify_claim(session, router, raw["claim_text"], sources, correlation_id=correlation_id)
        verified.append({**raw, **result})

    overall = compute_overall_verdict([c["verdict"] for c in verified])

    if overall == "FAIL":
        failed = [c for c in verified if c["verdict"] == "FAIL"]
        state_machine = ProjectStateMachine()
        await state_machine.transition(
            project, "NEED_REVIEW", actor=actor,
            reason="factcheck FAIL: " + "; ".join(c["claim_text"] for c in failed)[:500],
            session=session,
        )
        _notify(str(getattr(project, "id", "")), overall, failed)

    return {"claims": verified, "overall_verdict": overall}
