"""ClaimService -- Task 4-4 Steps 6-7: override + source-disable cascade (BR-3, BR-5).

Only this service writes ``claims.verdict``/``overridden_*`` -- routers
stay thin (rules/code-style.md). Both override and source-disable recompute
the project's ``overall_verdict`` + ``affected_claims`` synchronously in
the same call (BR-3/BR-5) -- never a background job.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.claim import Claim
from app.pipeline.nodes.factcheck.node import compute_overall_verdict

__all__ = ["ClaimNotFoundError", "ClaimService"]


class ClaimNotFoundError(Exception):
    pass


class ClaimService:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get(self, claim_id: Any) -> Claim | None:
        return await self._session.get(Claim, claim_id)

    async def list_for_project(self, project_id: Any) -> list[Claim]:
        result = await self._session.execute(
            select(Claim).where(Claim.project_id == project_id)
        )
        return list(result.scalars().all())

    async def _recompute_overall(self, project_id: Any) -> str:
        claims = await self.list_for_project(project_id)
        return compute_overall_verdict([c.verdict for c in claims])

    async def override(
        self, claim: Claim, *, verdict: str, reason: str, actor: str
    ) -> tuple[Claim, str, list[str]]:
        """BR-3: never deletes evidence; records audit; recomputes overall
        verdict synchronously. Returns (claim, overall_verdict, affected_claims)."""
        claim.verdict = verdict
        claim.overridden_by = actor
        claim.overridden_at = datetime.now(UTC)
        claim.override_reason = reason
        self._session.add(claim)
        await self._session.flush()

        overall = await self._recompute_overall(claim.project_id)
        return claim, overall, [str(claim.id)]

    async def recompute_after_source_change(
        self, project_id: Any, disabled_source_id: str
    ) -> tuple[str, list[str]]:
        """BR-5: disabling/deleting a source invalidates PASS/WARN verdicts
        that relied on it as evidence -- every claim citing it downgrades
        to WARN (its remaining evidence, if any, no longer includes the
        disabled source; conservatively treat it as no-longer-sufficient
        rather than silently keeping a stale PASS)."""
        claims = await self.list_for_project(project_id)
        affected: list[str] = []

        for claim in claims:
            evidence = claim.evidence or []
            cited = any(e.get("source_id") == disabled_source_id for e in evidence)
            if not cited:
                continue
            remaining_supporting_domains = {
                e.get("root_domain")
                for e in evidence
                if e.get("source_id") != disabled_source_id and not e.get("contradicts")
            }
            new_verdict = "PASS" if len(remaining_supporting_domains) >= 2 else "WARN"
            if new_verdict != claim.verdict:
                claim.verdict = new_verdict
                self._session.add(claim)
                affected.append(str(claim.id))

        if affected:
            await self._session.flush()

        overall = await self._recompute_overall(project_id)
        return overall, affected
