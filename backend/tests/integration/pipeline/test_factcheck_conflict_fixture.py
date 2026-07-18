"""Task 4-4 Step 8 -- exercises the reusable tests/fixtures/factcheck_conflict.json
asset end-to-end through run_factcheck (also used by 5-6/7-2/E2E per the
fixture's own description -- keep this test using the shared file, don't
let it drift into its own inline copy of the scenario).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.models.prompt import PromptVersion
from app.pipeline.nodes.factcheck.node import run_factcheck
from app.services.prompt_render import invalidate_all

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "factcheck_conflict.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _version(template: str, variables: list[str]) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(), prompt_id=uuid.uuid4(), version=1,
        template=template, variables=variables, is_active=True, created_by="system",
    )


class FakeSession:
    def __init__(self):
        self.versions = {
            "factcheck.extract_claims": _version(
                "{{ script_or_summary }} {{ topic }}", ["script_or_summary", "topic"]
            ),
            "factcheck.verify_claim": _version(
                "{{ claim_text }} {{ evidence_json }}", ["claim_text", "evidence_json"]
            ),
        }

    async def execute(self, stmt):
        params = stmt.compile().params
        name = params.get("name_1", params.get("name"))
        return _Result(self.versions.get(name))

    def add(self, obj):
        pass

    async def flush(self):
        pass


class FakeRouter:
    def __init__(self, fixture: dict):
        self._fixture = fixture
        self.calls = 0

    async def call(self, capability, method, *, tier="", args=(), kwargs=None, correlation_id=""):
        self.calls += 1
        if self.calls == 1:
            expected = self._fixture["expected"]
            return {
                "claims": [
                    {"claim_text": expected["claim_text"], "claim_type": expected["claim_type"]}
                ]
            }
        return {
            "verdict": self._fixture["expected"]["verdict"],
            "supporting_source_ids": ["s1"],
            "contradicting_source_ids": ["s2"],
            "explanation_vi": "2 nguon mau thuan ve ngay phat hanh",
        }


class FakeProject:
    def __init__(self):
        self.id = uuid.uuid4()
        self.status = "RESEARCHING"


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


@pytest.mark.asyncio
async def test_factcheck_conflict_fixture_produces_expected_outcome():
    fixture = _load_fixture()
    session = FakeSession()
    router = FakeRouter(fixture)
    project = FakeProject()

    result = await run_factcheck(
        session, router, project,
        fixture["script_or_summary"], fixture["sources"], fixture["topic"],
    )

    expected = fixture["expected"]
    assert result["overall_verdict"] == expected["overall_verdict"]
    assert result["claims"][0]["verdict"] == expected["verdict"]
    assert project.status == expected["project_status_after"]
