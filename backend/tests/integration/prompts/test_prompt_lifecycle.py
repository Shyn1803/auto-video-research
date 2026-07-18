"""Task 4-2 Step 10 -- AC1 end-to-end: create v2 -> activate -> next call
sees v2 with no restart -> rollback to v1 -> next call sees v1 again.

Combines PromptService (DB-facing) and prompt_render.get_active_prompt
(the cache nodes actually call) to prove the whole loop, not just each
piece in isolation.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.prompt import Prompt, PromptVersion
from app.services.prompt_render import get_active_prompt, invalidate_all
from app.services.prompt_service import PromptService


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


class InMemoryPromptDB:
    """A tiny in-memory stand-in for the prompts/prompt_versions tables,
    shared across both the write path (PromptService) and read path
    (get_active_prompt) the way a real Postgres instance would be."""

    def __init__(self, prompt: Prompt, versions: list[PromptVersion]):
        self.prompt = prompt
        self.versions = versions
        self.added: list = []
        self._raise_next = False

    def raise_integrity_error_once(self):
        self._raise_next = True

    async def execute(self, stmt):
        compiled_str = str(stmt).lower()
        if "update prompt_versions" in compiled_str:
            if self._raise_next:
                self._raise_next = False
                raise IntegrityError("stmt", {}, Exception("unique violation"))
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
        if "join prompts" in compiled_str or ("from prompt_versions" in compiled_str and "join" in compiled_str):
            # get_active_prompt's query: join Prompt, filter is_active
            active = next((v for v in self.versions if v.is_active), None)
            return _Result(scalar=active)
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
        self.versions.append(obj) if isinstance(obj, PromptVersion) else None

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


@pytest.fixture(autouse=True)
async def _clear_cache():
    await invalidate_all()
    yield
    await invalidate_all()


@pytest.mark.asyncio
async def test_ac1_edit_activate_v2_then_rollback_v1_no_restart():
    prompt = Prompt(id=uuid.uuid4(), name="script.generate", tier="strong")
    v1 = PromptVersion(
        id=uuid.uuid4(), prompt_id=prompt.id, version=1,
        template="v1 {{ x }}", variables=["x"], is_active=True,
        evaluated=True, created_by="system",
    )
    db = InMemoryPromptDB(prompt, [v1])
    svc = PromptService(db)

    # Baseline: get_active_prompt sees v1.
    active = await get_active_prompt(db, "script.generate")
    assert active.version == 1

    # Edit -> v2, then activate it.
    v2 = await svc.create_version(
        "script.generate", "v2 {{ x }}", ["x"], actor="admin-1"
    )
    assert v2.version == 2
    activated, warning = await svc.activate("script.generate", 2, actor="admin-1")
    assert activated.version == 2

    # No restart -- next get_active_prompt call sees v2 immediately (AC1).
    active_after = await get_active_prompt(db, "script.generate")
    assert active_after.version == 2
    assert active_after.template == "v2 {{ x }}"

    # Rollback = activate v1 again -- no new version created (BR-5).
    versions_before_rollback = len(db.versions)
    rolled_back, _ = await svc.activate("script.generate", 1, actor="admin-1")
    assert rolled_back.version == 1
    assert len(db.versions) == versions_before_rollback  # no copy made

    active_final = await get_active_prompt(db, "script.generate")
    assert active_final.version == 1
