"""PromptService -- Task 4-2 Step 6: create/activate/rollback + audit (BR-2, BR-5).

Only this service writes `prompt_versions.is_active` -- routers stay thin
(rules/code-style.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.models.prompt import Prompt, PromptVersion
from app.services import prompt_render
from app.services.prompt_render import PromptValidationError

__all__ = ["PromptValidationError", "PromptNotFoundError", "ActivateConflictError", "PromptService"]


class PromptNotFoundError(Exception):
    """Raised when a prompt name or version doesn't exist."""


class ActivateConflictError(Exception):
    """BR-1: two concurrent activates raced and this one lost (409-worthy)."""


class PromptService:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get_prompt(self, name: str) -> Prompt | None:
        return (
            await self._session.execute(select(Prompt).where(Prompt.name == name))
        ).scalar_one_or_none()

    async def list_versions(self, name: str) -> list[PromptVersion]:
        prompt = await self.get_prompt(name)
        if prompt is None:
            raise PromptNotFoundError(f"unknown prompt {name!r}")
        result = await self._session.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt.id)
            .order_by(PromptVersion.version)
        )
        return list(result.scalars().all())

    async def create_version(
        self, name: str, template: str, variables: list[str], actor: str
    ) -> PromptVersion:
        """New version, not activated (BR-3 validated before it's ever saved)."""
        prompt_render.validate_template(template, variables)  # raises PromptValidationError

        prompt = await self.get_prompt(name)
        if prompt is None:
            raise PromptNotFoundError(f"unknown prompt {name!r}")

        existing = await self.list_versions(name)
        next_version = (max((v.version for v in existing), default=0)) + 1

        version = PromptVersion(
            prompt_id=prompt.id,
            version=next_version,
            template=template,
            variables=variables,
            is_active=False,
            created_by=actor,
        )
        self._session.add(version)
        await self._session.flush()
        return version

    async def activate(
        self, name: str, version: int, actor: str
    ) -> tuple[PromptVersion, bool]:
        """Activate *version* of prompt *name*. Rollback is just calling this
        with an older version number -- never creates a copy (BR-5).

        Returns (activated_version, warning) where warning=True means the
        version hasn't run eval yet (BR-2: warn, don't hard-block).
        """
        prompt = await self.get_prompt(name)
        if prompt is None:
            raise PromptNotFoundError(f"unknown prompt {name!r}")

        target = (
            await self._session.execute(
                select(PromptVersion).where(
                    PromptVersion.prompt_id == prompt.id,
                    PromptVersion.version == version,
                )
            )
        ).scalar_one_or_none()
        if target is None:
            raise PromptNotFoundError(f"{name} has no version {version}")

        try:
            # Deactivate whichever version is currently active first, then
            # activate the target -- two statements, but the partial unique
            # index (migration 009) still catches a concurrent racer: if
            # another transaction's "activate" commits its own target
            # in between, this transaction's second UPDATE either no-ops
            # (already inactive) or raises IntegrityError on the unique
            # index, which is translated to ActivateConflictError (BR-1/AC5).
            await self._session.execute(
                update(PromptVersion)
                .where(PromptVersion.prompt_id == prompt.id, PromptVersion.is_active.is_(True))
                .values(is_active=False)
            )
            await self._session.execute(
                update(PromptVersion)
                .where(PromptVersion.id == target.id)
                .values(
                    is_active=True,
                    activated_by=actor,
                    activated_at=datetime.now(UTC),
                )
            )
            await self._session.flush()
        except IntegrityError as exc:
            raise ActivateConflictError(
                f"concurrent activate raced for prompt {name!r}"
            ) from exc

        await prompt_render.invalidate(name)

        target.is_active = True
        target.activated_by = actor
        warning = not target.evaluated
        return target, warning
