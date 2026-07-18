"""Prompt render + variable validation + active-prompt cache (Task 4-2 Steps 3-4).

BR-3: a template may only reference variables declared in its own
``variables[]`` -- validated at save time (400 naming the exact missing
variable(s)), not caught lazily at render time.

``get_active_prompt`` is a per-process cache invalidated the instant a
version is activated (AC1: no restart needed for a new active prompt to
take effect). Simplification flagged for later horizontal-scaling work:
this cache is process-local -- if the API runs multiple replicas, only the
replica that received the activate call invalidates immediately; others
serve their in-memory copy until their own cache entry is next queried
after a TTL/explicit refresh. Fine for the current single-process Phase 1
monolith (rules/architecture.md: "tach theo do dac, khong tach truoc").
"""

from __future__ import annotations

import asyncio
from typing import Any

from jinja2 import Environment, meta
from sqlalchemy import select

from app.models.prompt import Prompt, PromptVersion

_env = Environment()

# name -> PromptVersion, refreshed on cache miss or explicit invalidate().
_active_cache: dict[str, PromptVersion] = {}
_lock = asyncio.Lock()


class PromptValidationError(ValueError):
    """Raised when a template references a variable outside variables[] (BR-3)."""

    def __init__(self, missing: set[str]) -> None:
        self.missing = sorted(missing)
        super().__init__(
            f"template references undeclared variable(s): {', '.join(self.missing)}"
        )


def validate_template(template: str, variables: list[str]) -> None:
    """Raise PromptValidationError if *template* uses a variable not in *variables*."""
    ast = _env.parse(template)
    used = meta.find_undeclared_variables(ast)
    missing = used - set(variables)
    if missing:
        raise PromptValidationError(missing)


def render(template: str, context: dict[str, Any]) -> str:
    """Render *template* with Jinja2 against *context*."""
    return _env.from_string(template).render(**context)


async def invalidate(name: str) -> None:
    """Drop the cached active version for *name* (called on activate/rollback)."""
    async with _lock:
        _active_cache.pop(name, None)


async def invalidate_all() -> None:
    """Test/ops helper -- drop the whole cache."""
    async with _lock:
        _active_cache.clear()


async def get_active_prompt(session: Any, name: str) -> PromptVersion | None:
    """Return the active PromptVersion for *name*, using the process cache.

    Cache is populated on first miss and served until ``invalidate(name)``
    is called (by the activate/rollback service) -- never on a timer, so a
    new active version is visible on the very next call after activation
    (AC1), not eventually.
    """
    async with _lock:
        cached = _active_cache.get(name)
    if cached is not None:
        return cached

    result = await session.execute(
        select(PromptVersion)
        .join(Prompt, Prompt.id == PromptVersion.prompt_id)
        .where(Prompt.name == name, PromptVersion.is_active.is_(True))
    )
    version = result.scalar_one_or_none()
    if version is not None:
        async with _lock:
            _active_cache[name] = version
    return version
