"""Task 4-2 Step 6 + Step 10 -- PromptService: create/activate/rollback,
BR-1 race, BR-2 eval warning, BR-3 validation, BR-5 straight-line history.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.prompt import Prompt, PromptVersion
from app.services.prompt_render import invalidate_all
from app.services.prompt_service import (
    ActivateConflictError,
    PromptNotFoundError,
    PromptService,
    PromptValidationError,
)


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


class _Result:
    def __init__(self, scalar=None, scalars_all=None):
        self._scalar = scalar
        self._scalars_all = scalars_all or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class _S:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _S(self._scalars_all)


class FakeSession:
    """Purpose-built fake modeling one prompt with N versions in memory."""

    def __init__(self, prompt: Prompt, versions: list[PromptVersion]):
        self.prompt = prompt
        self.versions = versions
        self.added: list = []
        self.flush_count = 0
        self._raise_on_next_update = False

    def raise_integrity_error_on_next_update(self):
        self._raise_on_next_update = True

    async def execute(self, stmt):
        compiled_str = str(stmt).lower()
        if "update prompt_versions" in compiled_str:
            if self._raise_on_next_update:
                self._raise_on_next_update = False
                raise IntegrityError("stmt", {}, Exception("unique violation"))
            # apply a crude simulation: "is_active=false" clears all,
            # "is_active=true" sets the one matching id in the compiled params
            params = stmt.compile().params
            if params.get("is_active") is False:
                for v in self.versions:
                    v.is_active = False
            elif params.get("is_active") is True:
                target_id = params.get("id_1") or params.get("id")
                for v in self.versions:
                    if str(v.id) == str(target_id):
                        v.is_active = True
                        v.activated_by = params.get("activated_by")
            return _Result()
        if "from prompts" in compiled_str:
            return _Result(scalar=self.prompt)
        if "from prompt_versions" in compiled_str:
            params = stmt.compile().params
            if "version_1" in params or "version" in params:
                wanted = params.get("version_1", params.get("version"))
                match = next((v for v in self.versions if v.version == wanted), None)
                return _Result(scalar=match)
            return _Result(scalars_all=sorted(self.versions, key=lambda v: v.version))
        return _Result()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_count += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


def _prompt() -> Prompt:
    return Prompt(id=uuid.uuid4(), name="script.generate", tier="strong")


def _version(prompt: Prompt, version: int, *, active: bool, evaluated: bool = False) -> PromptVersion:
    return PromptVersion(
        id=uuid.uuid4(),
        prompt_id=prompt.id,
        version=version,
        template=f"v{version} {{{{ x }}}}",
        variables=["x"],
        is_active=active,
        evaluated=evaluated,
        created_by="system",
    )


@pytest.mark.asyncio
async def test_create_version_validates_undeclared_variable_400():
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True)
    session = FakeSession(prompt, [v1])
    svc = PromptService(session)

    with pytest.raises(PromptValidationError) as exc_info:
        await svc.create_version(
            "script.generate", "hi {{ bien_la }}", ["x"], actor="admin-1"
        )
    assert exc_info.value.missing == ["bien_la"]


@pytest.mark.asyncio
async def test_create_version_increments_version_number():
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True)
    session = FakeSession(prompt, [v1])
    svc = PromptService(session)

    v2 = await svc.create_version(
        "script.generate", "hi {{ x }}", ["x"], actor="admin-1"
    )
    assert v2.version == 2
    assert v2.is_active is False  # created, not yet activated


@pytest.mark.asyncio
async def test_activate_flips_active_flag_straight_line_no_copy():
    """BR-5: rollback = activate an older version -- no new row created."""
    prompt = _prompt()
    v1 = _version(prompt, 1, active=False)
    v2 = _version(prompt, 2, active=True)
    session = FakeSession(prompt, [v1, v2])
    svc = PromptService(session)

    activated, warning = await svc.activate("script.generate", 1, actor="admin-1")

    assert activated.version == 1
    assert v1.is_active is True
    assert v2.is_active is False
    assert len(session.added) == 0  # no new PromptVersion row created (BR-5)


@pytest.mark.asyncio
async def test_activate_unevaluated_version_warns_but_does_not_block():
    """BR-2: activating a version that hasn't run eval succeeds with a warning."""
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True, evaluated=True)
    v2 = _version(prompt, 2, active=False, evaluated=False)
    session = FakeSession(prompt, [v1, v2])
    svc = PromptService(session)

    activated, warning = await svc.activate("script.generate", 2, actor="admin-1")
    assert activated.version == 2
    assert warning is True  # not evaluated -> warn, not a 4xx


@pytest.mark.asyncio
async def test_activate_records_who_and_when_audit_trail():
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True)
    session = FakeSession(prompt, [v1])
    svc = PromptService(session)

    activated, _ = await svc.activate("script.generate", 1, actor="admin-42")
    assert activated.activated_by == "admin-42"


@pytest.mark.asyncio
async def test_activate_unknown_version_raises_not_found():
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True)
    session = FakeSession(prompt, [v1])
    svc = PromptService(session)

    with pytest.raises(PromptNotFoundError):
        await svc.activate("script.generate", 99, actor="admin-1")


@pytest.mark.asyncio
async def test_br1_concurrent_activate_race_one_wins_other_conflicts():
    """AC5: simulate the second of two concurrent activate calls losing to
    the DB partial-unique-index race -- translated to ActivateConflictError."""
    prompt = _prompt()
    v1 = _version(prompt, 1, active=True)
    v2 = _version(prompt, 2, active=False)
    session = FakeSession(prompt, [v1, v2])
    svc = PromptService(session)

    session.raise_integrity_error_on_next_update()
    with pytest.raises(ActivateConflictError):
        await svc.activate("script.generate", 2, actor="admin-1")
