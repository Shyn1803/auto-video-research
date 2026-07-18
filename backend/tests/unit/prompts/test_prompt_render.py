"""Task 4-2 Steps 3-4 -- Jinja2 render + variable validation (BR-3) + cache (AC1)."""

from __future__ import annotations

import uuid

import pytest

from app.models.prompt import PromptVersion
from app.services import prompt_render
from app.services.prompt_render import (
    PromptValidationError,
    get_active_prompt,
    invalidate,
    invalidate_all,
    render,
    validate_template,
)


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


def test_validate_template_passes_when_all_vars_declared():
    validate_template("hello {{ topic }}", ["topic"])  # no raise


def test_validate_template_raises_400_worthy_error_naming_missing_var():
    """AC2: template with {{ bien_la }} not declared -> error naming exactly that var."""
    with pytest.raises(PromptValidationError) as exc_info:
        validate_template("hello {{ bien_la }}", ["topic"])
    assert exc_info.value.missing == ["bien_la"]
    assert "bien_la" in str(exc_info.value)


def test_render_substitutes_declared_variables():
    out = render("Xin chao {{ name }}!", {"name": "The Gioi"})
    assert out == "Xin chao The Gioi!"


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, version: PromptVersion | None):
        self._version = version
        self.execute_count = 0

    async def execute(self, _stmt):
        self.execute_count += 1
        return FakeResult(self._version)


def _make_version(template: str = "v", version: int = 1) -> PromptVersion:
    v = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        version=version,
        template=template,
        variables=[],
        is_active=True,
        created_by="system",
    )
    return v


@pytest.mark.asyncio
async def test_get_active_prompt_caches_after_first_query():
    v1 = _make_version(version=1)
    session = FakeSession(v1)

    first = await get_active_prompt(session, "script.generate")
    second = await get_active_prompt(session, "script.generate")

    assert first is v1
    assert second is v1
    assert session.execute_count == 1  # second call served from cache


@pytest.mark.asyncio
async def test_activate_invalidates_cache_and_next_call_sees_new_version():
    """AC1: activate v2 -> immediate next get_active_prompt call returns v2,
    no restart/TTL wait needed."""
    v1 = _make_version(version=1)
    session = FakeSession(v1)
    cached = await get_active_prompt(session, "script.generate")
    assert cached.version == 1

    # "activate v2" -- service would flip is_active flags in DB, then call invalidate()
    v2 = _make_version(version=2)
    session_v2 = FakeSession(v2)
    await invalidate("script.generate")

    result = await get_active_prompt(session_v2, "script.generate")
    assert result.version == 2
