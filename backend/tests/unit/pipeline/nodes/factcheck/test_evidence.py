"""Task 4-4 Step 4 -- evidence gathering (keyword-overlap stand-in) + root_domain."""

from __future__ import annotations

from app.pipeline.nodes.factcheck.evidence import gather_evidence, root_domain


def test_root_domain_strips_subdomain():
    assert root_domain("https://blog.openai.com/x") == "openai.com"
    assert root_domain("https://openai.com/y") == "openai.com"


def test_gather_evidence_finds_matching_source():
    sources = [
        {"id": "s1", "url": "https://a.com/x", "content": "Model X achieves 92.5 percent on SWE-bench."},
        {"id": "s2", "url": "https://b.com/y", "content": "Unrelated cooking article about bread."},
    ]
    evidence = gather_evidence("Model X achieves 92.5 percent on SWE-bench", sources)
    assert len(evidence) == 1
    assert evidence[0]["source_id"] == "s1"


def test_gather_evidence_empty_when_no_source_mentions_claim():
    sources = [{"id": "s1", "url": "https://a.com/x", "content": "Completely unrelated content here."}]
    evidence = gather_evidence("SWE-bench score of ninety two", sources)
    assert evidence == []


def test_gather_evidence_marks_partial_content_and_trust():
    sources = [
        {
            "id": "s1", "url": "https://official.com/x", "trusted": True,
            "partial_content": True, "content": "SWE-bench result reported today.",
        }
    ]
    evidence = gather_evidence("SWE-bench result", sources)
    assert evidence[0]["source_trusted"] is True
    assert evidence[0]["partial_content"] is True
