"""Task 4-4 Step 5/8 -- AC1: 2 sources disagree on a date -> claim FAIL,
project NEED_REVIEW, notify (log) fires.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.factcheck.node import compute_overall_verdict, run_factcheck
from app.services.prompt_render import invalidate_all


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _version(name: str, template: str, variables: list[str]) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template=template, variables=variables, is_active=True, created_by="system",
    )


class FakeSession:
    def __init__(self):
        self.versions = {
            "factcheck.extract_claims": _version(
                "factcheck.extract_claims", "{{ script_or_summary }} {{ topic }}",
                ["script_or_summary", "topic"],
            ),
            "factcheck.verify_claim": _version(
                "factcheck.verify_claim", "{{ claim_text }} {{ evidence_json }}",
                ["claim_text", "evidence_json"],
            ),
        }
        self.added = []

    async def execute(self, stmt):
        compiled_str = str(stmt).lower()
        params = stmt.compile().params
        name = params.get("name_1", params.get("name"))
        return _Result(self.versions.get(name))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


class FakeRouter:
    """Returns extract-claims output first, then per-claim verify output."""

    def __init__(self):
        self.calls = 0

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.calls += 1
        prompt = args[0]
        if "script_or_summary" not in prompt and "evidence_json" not in prompt:
            pass
        if self.calls == 1:
            return {"claims": [{"claim_text": "Released on January 15 2026", "claim_type": "release_date"}]}
        return {
            "verdict": "FAIL",
            "supporting_source_ids": ["s1"],
            "contradicting_source_ids": ["s2"],
            "explanation_vi": "2 nguon mau thuan ve ngay phat hanh",
        }


class FakeProject:
    def __init__(self):
        self.id = uuid.uuid4()
        self.status = "RESEARCHING"


def test_compute_overall_verdict_rules():
    assert compute_overall_verdict([]) == "PASS"
    assert compute_overall_verdict(["PASS", "PASS"]) == "PASS"
    assert compute_overall_verdict(["PASS", "WARN"]) == "WARN"
    assert compute_overall_verdict(["PASS", "WARN", "FAIL"]) == "FAIL"


@pytest.mark.asyncio
async def test_ac1_conflicting_sources_yields_fail_and_need_review(caplog):
    session = FakeSession()
    router = FakeRouter()
    project = FakeProject()
    sources = [
        {"id": "s1", "url": "https://a.com/x", "content": "Released on January 15 2026."},
        {"id": "s2", "url": "https://b.com/y", "content": "Released on January 20 2026."},
    ]

    import logging

    with caplog.at_level(logging.WARNING, logger="avr.factcheck.node"):
        result = await run_factcheck(
            session, router, project,
            "Model released on January 15 2026", sources, "AI model release",
        )

    assert result["overall_verdict"] == "FAIL"
    assert result["claims"][0]["verdict"] == "FAIL"
    assert project.status == "NEED_REVIEW"
    assert any("factcheck notify" in r.message for r in caplog.records)
