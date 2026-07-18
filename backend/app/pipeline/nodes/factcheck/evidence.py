"""Evidence gathering -- Task 4-4 Step 4.

Simplification (flagged, not hidden): "real" embedding-similarity search
(BGE-M3 cosine similarity against each source's content, matching the
dedupe pattern in app/pipeline/nodes/research/dedupe.py) needs a live
embedding provider call per claim x source pair, which isn't wired into
this pipeline yet (no live embedding service in this sandbox to validate
against either). This module uses a keyword-overlap heuristic instead --
a source is "evidence" for a claim if a significant word from the claim
text appears in the source's content/summary. Swap the matching function
for a real embedding search once 4-6/later wiring makes that available;
the ``evidence_json`` shape this produces (source_id/quote/source_trusted)
is exactly what factcheck.verify_claim expects either way.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "to",
    "and", "or", "for", "with", "at", "by", "from", "that", "this",
}


def root_domain(url: str) -> str:
    """Extract the registrable-ish domain -- 'blog.openai.com' and
    'openai.com' both -> 'openai.com' (BR-1: same root domain = 1 source)."""
    netloc = urlparse(url).netloc.lower()
    parts = netloc.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return netloc


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\.\-]{2,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _find_quote(content: str, words: set[str]) -> str | None:
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        sentence_words = _significant_words(sentence)
        if sentence_words & words:
            return sentence.strip()[:300]
    return None


def gather_evidence(claim_text: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return evidence items {source_id, quote, source_trusted, root_domain}
    for every source whose content overlaps with *claim_text*'s
    significant words (BR-4: empty list -> orphan claim, handled by verify.py)."""
    claim_words = _significant_words(claim_text)
    if not claim_words:
        return []

    evidence: list[dict[str, Any]] = []
    for source in sources:
        content = source.get("content") or source.get("summary_vi") or ""
        quote = _find_quote(content, claim_words)
        if quote is None:
            continue
        evidence.append(
            {
                "source_id": source.get("id") or source.get("url"),
                "quote": quote,
                "source_trusted": bool(source.get("trusted", False)),
                "root_domain": root_domain(source.get("url", "")),
                "partial_content": bool(source.get("partial_content", False)),
            }
        )
    return evidence
