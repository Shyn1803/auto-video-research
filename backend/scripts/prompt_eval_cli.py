"""CLI: `make prompt-eval PROMPT=script.generate V=2` (Task 4-2 Step 9, AC4).

Renders the requested prompt version against the 10-topic fixture
(tests/fixtures/eval_topics.json) and prints a comparison table -- see
app/services/prompt_eval.py for exactly what "eval" means here (render-level
checks, not LLM-graded output; that's the documented v1.1 follow-up).

Looks the version up in the DB first (the real source of truth once a
prompt has been edited/activated past v1); if the DB is unreachable (no
Postgres in this sandbox) and the requested version is 1, falls back to
the seed data in app/pipeline/prompts/seed.py so the command still works
in a DB-less dev environment for the common case.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.prompts.seed import PROMPT_SEEDS  # noqa: E402
from app.services.prompt_eval import build_eval_table, format_eval_table  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eval_topics.json"


def _seed_fallback(prompt_name: str, version: int) -> tuple[str, list[str]] | None:
    if version != 1:
        return None
    seed = next((p for p in PROMPT_SEEDS if p["name"] == prompt_name), None)
    if seed is None:
        return None
    return seed["template"], seed["variables"]


async def _fetch_from_db(prompt_name: str, version: int) -> tuple[str, list[str]] | None:
    try:
        from sqlalchemy import select

        from app.core.config import get_settings
        from app.core.database import Database
        from app.models.prompt import Prompt, PromptVersion

        db = Database(get_settings().database_url)
        async with db.session() as session:
            result = await session.execute(
                select(PromptVersion)
                .join(Prompt, Prompt.id == PromptVersion.prompt_id)
                .where(Prompt.name == prompt_name, PromptVersion.version == version)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return row.template, row.variables
    except Exception as exc:  # noqa: BLE001 -- DB may genuinely be unreachable in dev
        print(f"(DB lookup unavailable: {exc} -- trying seed fallback)", file=sys.stderr)
        return None


async def main_async(prompt_name: str, version: int) -> int:
    found = await _fetch_from_db(prompt_name, version)
    if found is None:
        found = _seed_fallback(prompt_name, version)
    if found is None:
        print(
            f"error: {prompt_name!r} version {version} not found in DB "
            "and no seed fallback available",
            file=sys.stderr,
        )
        return 1

    template, variables = found
    topics = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    rows = build_eval_table(template, variables, topics)
    print(format_eval_table(rows))

    failures = [r for r in rows if not r["parse_ok"]]
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prompt eval comparison table")
    parser.add_argument("--prompt", required=True, dest="prompt_name")
    parser.add_argument("--version", required=True, type=int, dest="version")
    args = parser.parse_args()
    return asyncio.run(main_async(args.prompt_name, args.version))


if __name__ == "__main__":
    raise SystemExit(main())
