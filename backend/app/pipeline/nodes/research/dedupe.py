"""Dedupe -- url_hash exact match, then embedding similarity (Task 4-3 Step 4, BR-2).

Two passes:
1. Exact ``url_hash`` -- same normalized URL crawled twice (e.g. via two
   different connectors) collapses to one row.
2. Embedding cosine similarity >= threshold (default 0.92, "Decisions
   already locked") -- near-duplicate *content* from different URLs.
   Tie-break: keep the trusted-domain source; if both/neither trusted,
   keep the newer one (BR-2).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urlunparse

DEFAULT_SIMILARITY_THRESHOLD = 0.92


@dataclass
class SourceCandidate:
    id: str
    url: str
    url_hash: str
    trusted: bool = False
    published_at: datetime | None = None
    embedding: list[float] | None = None


def normalize_url(url: str) -> str:
    """Lowercase scheme/host, drop fragment and trailing slash -- enough to
    catch the common "same article, different query string / anchor" case
    without being clever about tracking-param stripping (out of scope)."""
    parsed = urlparse(url.strip())
    normalized = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            parsed.query,
            "",  # drop fragment
        )
    )
    return normalized


def url_hash(url: str) -> str:
    """sha256(normalized url) -- matches sources.url_hash (database-schema.md)."""
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keep_better(a: SourceCandidate, b: SourceCandidate) -> SourceCandidate:
    """BR-2 tie-break: trusted wins; if tie, newer wins."""
    if a.trusted != b.trusted:
        return a if a.trusted else b
    a_pub = a.published_at or datetime.min
    b_pub = b.published_at or datetime.min
    return a if a_pub >= b_pub else b


def dedupe_by_url_hash(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """Keep the first-seen candidate per exact url_hash."""
    seen: dict[str, SourceCandidate] = {}
    for c in candidates:
        if c.url_hash not in seen:
            seen[c.url_hash] = c
    return list(seen.values())


def dedupe_by_similarity(
    candidates: list[SourceCandidate],
    *,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[SourceCandidate]:
    """Merge near-duplicate content by embedding cosine similarity (BR-2)."""
    kept: list[SourceCandidate] = []
    for candidate in candidates:
        merged_index: int | None = None
        for i, existing in enumerate(kept):
            if candidate.embedding is None or existing.embedding is None:
                continue
            if cosine_similarity(candidate.embedding, existing.embedding) >= threshold:
                merged_index = i
                break
        if merged_index is None:
            kept.append(candidate)
        else:
            kept[merged_index] = _keep_better(kept[merged_index], candidate)
    return kept


def dedupe_sources(
    candidates: list[SourceCandidate],
    *,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[SourceCandidate]:
    """Full dedupe pipeline: exact url_hash, then embedding similarity."""
    return dedupe_by_similarity(dedupe_by_url_hash(candidates), threshold=threshold)
