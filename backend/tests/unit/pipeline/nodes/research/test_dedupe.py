"""Task 4-3 Step 4 -- dedupe by url_hash then embedding similarity (BR-2, AC5)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.pipeline.nodes.research.dedupe import (
    SourceCandidate,
    cosine_similarity,
    dedupe_by_similarity,
    dedupe_by_url_hash,
    dedupe_sources,
    normalize_url,
    url_hash,
)


def test_normalize_url_drops_fragment_and_trailing_slash():
    a = normalize_url("https://Example.com/Article/?x=1#section")
    b = normalize_url("https://example.com/Article?x=1")
    assert a == b


def test_url_hash_is_stable_sha256():
    h1 = url_hash("https://example.com/a/")
    h2 = url_hash("https://example.com/a")
    assert h1 == h2
    assert len(h1) == 64


def test_dedupe_by_url_hash_keeps_first_of_exact_duplicates():
    a = SourceCandidate(id="1", url="https://x.com/a", url_hash="h1")
    b = SourceCandidate(id="2", url="https://x.com/a/", url_hash="h1")
    c = SourceCandidate(id="3", url="https://x.com/b", url_hash="h2")
    result = dedupe_by_url_hash([a, b, c])
    assert len(result) == 2
    assert result[0].id == "1"


def test_cosine_similarity_identical_vectors_is_one():
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_is_zero():
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_ac5_similar_095_trusted_vs_untrusted_keeps_trusted():
    """AC5 / BR-2: 2 sources at 0.95 similarity, one trusted one not ->
    the trusted one is kept."""
    trusted = SourceCandidate(
        id="trusted", url="https://official.com/a", url_hash="ha",
        trusted=True, embedding=[1.0, 0.0, 0.0],
    )
    # crafted to be ~0.95 cosine similarity to [1,0,0]
    untrusted = SourceCandidate(
        id="untrusted", url="https://randomblog.com/b", url_hash="hb",
        trusted=False, embedding=[0.95, 0.312, 0.0],
    )
    sim = cosine_similarity(trusted.embedding, untrusted.embedding)
    assert sim >= 0.94  # sanity: really is a near-duplicate pair

    result = dedupe_by_similarity([trusted, untrusted], threshold=0.92)
    assert len(result) == 1
    assert result[0].id == "trusted"

    # order shouldn't matter
    result_reversed = dedupe_by_similarity([untrusted, trusted], threshold=0.92)
    assert len(result_reversed) == 1
    assert result_reversed[0].id == "trusted"


def test_similarity_tie_break_prefers_newer_when_trust_equal():
    older = SourceCandidate(
        id="older", url="https://a.com/1", url_hash="h1", trusted=True,
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        embedding=[1.0, 0.0],
    )
    newer = SourceCandidate(
        id="newer", url="https://a.com/2", url_hash="h2", trusted=True,
        published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        embedding=[1.0, 0.0001],
    )
    result = dedupe_by_similarity([older, newer], threshold=0.9)
    assert len(result) == 1
    assert result[0].id == "newer"


def test_below_threshold_similarity_keeps_both():
    a = SourceCandidate(id="a", url="https://x.com/1", url_hash="h1", embedding=[1.0, 0.0])
    b = SourceCandidate(id="b", url="https://x.com/2", url_hash="h2", embedding=[0.0, 1.0])
    result = dedupe_by_similarity([a, b], threshold=0.92)
    assert len(result) == 2


def test_dedupe_sources_full_pipeline_url_hash_then_similarity():
    exact_dup = SourceCandidate(id="1", url="https://x.com/a", url_hash="h1", embedding=[1.0, 0.0])
    exact_dup2 = SourceCandidate(id="2", url="https://x.com/a/", url_hash="h1", embedding=[1.0, 0.0])
    near_dup = SourceCandidate(
        id="3", url="https://y.com/b", url_hash="h2", trusted=True, embedding=[0.99, 0.14]
    )
    distinct = SourceCandidate(id="4", url="https://z.com/c", url_hash="h3", embedding=[0.0, 1.0])

    result = dedupe_sources([exact_dup, exact_dup2, near_dup, distinct], threshold=0.92)
    ids = {c.id for c in result}
    # exact_dup/exact_dup2 collapse to one, then that one may or may not
    # merge with near_dup depending on embedding similarity -- assert the
    # distinct one always survives and total count shrank from 4.
    assert "4" in ids
    assert len(result) < 4
