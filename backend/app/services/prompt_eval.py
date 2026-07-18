"""Prompt eval table -- Task 4-2 Step 9 (AC4).

Out of scope per the task ("Out: eval tu cham bang LLM (v1.1)"): this does
NOT call an LLM to grade output. It renders the chosen prompt version
against each of the 10 fixture topics and reports render-level metrics
(length, parse-ok i.e. did it render without a missing variable, numbers
preserved i.e. does the rendered text still contain the topic's original
digits) so an admin can eyeball the rendered prompts side-by-side before
manually running them through an LLM and comparing real output. Automated
LLM-graded comparison is the documented v1.1 follow-up.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from app.services.prompt_render import render


class EvalRow(TypedDict):
    topic: str
    rendered_length: int
    parse_ok: bool
    numbers_preserved: bool
    error: str | None


_DIGIT_RE = re.compile(r"\d+")


def _numbers_preserved(topic: str, rendered: str) -> bool:
    """Every digit sequence in the topic string must still appear in the
    rendered prompt -- a template that drops/reformats numbers would fail
    silently otherwise (docs/specs/prompts.md's own "so lieu giu nguyen"
    rule, checked here at the template-render level as a proxy)."""
    topic_numbers = set(_DIGIT_RE.findall(topic))
    if not topic_numbers:
        return True
    rendered_numbers = set(_DIGIT_RE.findall(rendered))
    return topic_numbers.issubset(rendered_numbers)


def build_eval_table(
    template: str, variables: list[str], topics: list[dict[str, Any]]
) -> list[EvalRow]:
    """Render *template* once per topic row, filling any declared variable
    the topic fixture doesn't provide with a visible placeholder so a
    missing-context bug in the fixture shows up as `<var_name>` in the
    output instead of a silent KeyError/empty string."""
    rows: list[EvalRow] = []
    for topic_row in topics:
        context = dict(topic_row)
        for var in variables:
            context.setdefault(var, f"<{var}>")
        topic = str(topic_row.get("topic", "<no topic>"))
        try:
            rendered = render(template, context)
            rows.append(
                EvalRow(
                    topic=topic,
                    rendered_length=len(rendered),
                    parse_ok=True,
                    numbers_preserved=_numbers_preserved(topic, rendered),
                    error=None,
                )
            )
        except Exception as exc:  # noqa: BLE001 -- surfaced in the table, not raised
            rows.append(
                EvalRow(
                    topic=topic,
                    rendered_length=0,
                    parse_ok=False,
                    numbers_preserved=False,
                    error=str(exc),
                )
            )
    return rows


def format_eval_table(rows: list[EvalRow]) -> str:
    """Render *rows* as a simple fixed-width text table for terminal output."""
    header = f"{'topic':<60} | {'len':>5} | {'parse_ok':>8} | {'nums_ok':>7} | error"
    lines = [header, "-" * len(header)]
    for row in rows:
        topic_display = row["topic"][:58]
        lines.append(
            f"{topic_display:<60} | {row['rendered_length']:>5} | "
            f"{str(row['parse_ok']):>8} | {str(row['numbers_preserved']):>7} | "
            f"{row['error'] or ''}"
        )
    return "\n".join(lines)
