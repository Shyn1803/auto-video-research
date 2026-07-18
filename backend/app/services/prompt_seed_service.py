"""Seed the 8 prompts from docs/specs/prompts.md into the DB (Task 4-2 Step 2).

Idempotent: re-running against an already-seeded DB is a no-op per prompt
that already exists (by name) -- safe to call on every app startup or from
a one-off script, never duplicates rows.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from app.models.prompt import Prompt, PromptVersion
from app.pipeline.prompts.seed import PROMPT_SEEDS

logger = logging.getLogger(__name__)


async def seed_prompts(session: Any, *, actor: str = "system") -> list[Prompt]:
    """Insert any prompt from PROMPT_SEEDS not already present (by name).

    Each newly-created prompt gets exactly one version (v1, active=true) --
    matches docs/specs/prompts.md's "Moi prompt seed la version 1,
    is_active=true" (Quan tri prompt section).
    """
    created: list[Prompt] = []
    for seed in PROMPT_SEEDS:
        existing = (
            await session.execute(select(Prompt).where(Prompt.name == seed["name"]))
        ).scalar_one_or_none()
        if existing is not None:
            continue

        prompt = Prompt(
            name=seed["name"], tier=seed["tier"], description=seed["description"]
        )
        session.add(prompt)
        await session.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version=1,
            template=seed["template"],
            variables=seed["variables"],
            is_active=True,
            created_by=actor,
            activated_by=actor,
        )
        session.add(version)
        await session.flush()

        created.append(prompt)
        logger.info("seeded prompt %s v1 (active)", seed["name"])

    return created
