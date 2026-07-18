"""Task 4-2 Step 2 -- seed content + idempotency."""

from __future__ import annotations

import pytest
from jinja2 import Environment, meta

from app.pipeline.prompts.seed import PROMPT_SEEDS
from app.services.prompt_seed_service import seed_prompts


def test_exactly_eight_prompts_seeded():
    names = [p["name"] for p in PROMPT_SEEDS]
    assert names == [
        "research.summarize",
        "ranking.score",
        "factcheck.extract_claims",
        "factcheck.verify_claim",
        "outline.generate",
        "script.generate",
        "storyboard.generate",
        "asset.query",
    ]


def test_every_template_only_references_declared_variables():
    """Sanity check for BR-3 against the seed data itself -- seeding must
    never violate its own variable-declaration rule."""
    env = Environment()
    for p in PROMPT_SEEDS:
        ast = env.parse(p["template"])
        used = meta.find_undeclared_variables(ast)
        missing = used - set(p["variables"])
        assert not missing, f"{p['name']}: undeclared vars used {missing}"


def test_templates_are_non_empty_and_tier_valid():
    for p in PROMPT_SEEDS:
        assert p["template"].strip()
        assert p["tier"] in {"cheap", "strong", "embedding"}


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self):
        self.added: list = []
        self.flush_count = 0

    async def execute(self, _stmt):
        # look up by name against what's already been "added" as a Prompt
        from app.models.prompt import Prompt

        for obj in self.added:
            if isinstance(obj, Prompt):
                return _Result(obj)
        return _Result(None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                import uuid

                obj.id = uuid.uuid4()


@pytest.mark.asyncio
async def test_seed_creates_eight_prompts_each_with_one_active_version():
    session = FakeSession()
    # FakeSession's execute() always matches against *any* Prompt added so
    # far -- to exercise "8 distinct prompts get created" honestly we need
    # per-name lookup; swap in a smarter fake here.
    class PerNameSession(FakeSession):
        async def execute(self, stmt):
            # crude: pull the compared name out of the stmt's compile params
            compiled = stmt.compile()
            name = list(compiled.params.values())[0]
            from app.models.prompt import Prompt

            match = next(
                (o for o in self.added if isinstance(o, Prompt) and o.name == name),
                None,
            )
            return _Result(match)

    session = PerNameSession()
    created = await seed_prompts(session, actor="system")
    assert len(created) == 8

    from app.models.prompt import Prompt, PromptVersion

    prompts = [o for o in session.added if isinstance(o, Prompt)]
    versions = [o for o in session.added if isinstance(o, PromptVersion)]
    assert len(prompts) == 8
    assert len(versions) == 8
    assert all(v.is_active for v in versions)
    assert all(v.version == 1 for v in versions)


@pytest.mark.asyncio
async def test_seed_is_idempotent_on_rerun():
    class PerNameSession(FakeSession):
        async def execute(self, stmt):
            compiled = stmt.compile()
            name = list(compiled.params.values())[0]
            from app.models.prompt import Prompt

            match = next(
                (o for o in self.added if isinstance(o, Prompt) and o.name == name),
                None,
            )
            return _Result(match)

    session = PerNameSession()
    first = await seed_prompts(session, actor="system")
    second = await seed_prompts(session, actor="system")
    assert len(first) == 8
    assert len(second) == 0  # everything already existed -> no-op
