"""Write-node context builder -- Task 4-5 Step 2 (BR-1).

BR-1: "Claim FAIL 'loại khỏi video' -> nội dung đó không xuất hiện
outline/script (lọc context trước prompt)." This is a deterministic,
pre-prompt filter -- not something the LLM is trusted to self-censor
(same "AI never decides structure/rules alone" posture task 4-4's
verify.py docstring already established for fact-check gates).

Two things get filtered here, both *before* any prompt is rendered:
1. ``claims_passed`` (the outline.generate prompt variable, docs/specs/
   prompts.md §5) -- FAIL claims never enter this list. WARN claims do
   (Scope In: "chỉ claim PASS/WARN-đã-duyệt" -- WARN claims that have
   gone through fact-check review, as opposed to PENDING/unverified,
   are usable; BR-4's disclosure-phrase requirement is what keeps their
   use honest, not exclusion).
2. ``sources`` used to build ``ranked_summaries`` -- any source whose
   text is what a FAIL claim was actually about must not leak the failed
   content back in through the raw source summary, even though the claim
   itself was filtered out of ``claims_passed``.
"""

from __future__ import annotations

from typing import Any

_STOPWORDS = {
    "va", "voi", "cua", "la", "co", "khong", "duoc", "cho", "de", "nay",
    "the", "and", "with", "of", "is", "are", "not", "for", "this", "that",
}


def _keywords(text: str, *, min_len: int = 4) -> set[str]:
    """Lowercased, punctuation-stripped, stopword-filtered word set."""
    words = "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    return {w for w in words if len(w) >= min_len and w not in _STOPWORDS}


def _source_text(source: dict[str, Any]) -> str:
    return " ".join(
        str(source.get(k, "")) for k in ("summary_vi", "title", "content", "text")
    )


def _source_mentions_fail_claim(source: dict[str, Any], fail_keywords: set[str]) -> bool:
    """A source is considered tied to a FAIL claim if it shares at least one
    distinctive (len>=4) keyword with that claim's text -- a lightweight,
    deterministic heuristic (not semantic matching) since the actual
    source<->claim link (evidence[].source_id) only tells us which sources
    were *checked* against a claim, not which ones authored the failed
    wording in the first place.
    """
    if not fail_keywords:
        return False
    return bool(_keywords(_source_text(source)) & fail_keywords)


def build_write_context(
    claims: list[dict[str, Any]], sources: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return ``{"claims_passed": [...], "sources": [...]}`` with all FAIL
    claim content removed before it ever reaches an outline/script prompt.
    """
    fail_claims = [c for c in claims if c.get("verdict") == "FAIL"]
    usable_claims = [c for c in claims if c.get("verdict") in ("PASS", "WARN")]

    fail_keywords: set[str] = set()
    for c in fail_claims:
        fail_keywords |= _keywords(c.get("claim_text", ""))

    filtered_sources = [
        s for s in sources if not _source_mentions_fail_claim(s, fail_keywords)
    ]

    return {"claims_passed": usable_claims, "sources": filtered_sources}
