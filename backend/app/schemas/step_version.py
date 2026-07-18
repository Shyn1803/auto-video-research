"""Content-JSONB schemas for `step_versions` — Task 4-5 Step 1.

`StepVersion.content` (app/models/step_version.py) is an untyped JSONB
column shared by every pipeline step ("research", "outline", "script",
"storyboard", "scene_set", "produce", "render", "publish") — this module
does **not** replace that column with a typed one (that would be a much
bigger, unrelated migration). It defines the two content shapes the write
node (outline/script) actually produces, plus the single normalized
`warnings[]` shape every BR in this task emits through (BR-2 symbol-leak,
BR-3 title-truncation, BR-4 WARN-disclosure-missing, plus Step 4's
number-set mismatch) — so a consumer (API/FE) parses one warning shape
regardless of which validator produced it, instead of a different ad hoc
dict per BR.

Contract change (task 4-5): see docs/specs/api-spec.md §3 "Task 4-5
contract change" note for the semver/migration statement required by
rules/documentation.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

WarningType = Literal[
    "number_set_mismatch",
    "voice_over_symbol_leak",
    "title_truncated",
    "warn_claim_disclosure_missing",
]


class ContentWarning(BaseModel):
    """One warning entry — never a hard failure (see task 4-5 "Decisions
    already locked": no hard block on number-set mismatch after retry;
    same "flag, don't block" posture applies to every warning type here).
    """

    type: WarningType
    detail: str


class OutlineSections(BaseModel):
    """The 7 always-present narrative sections from `outline.generate`
    (docs/specs/prompts.md §5) plus the one optional/nullable section.

    `controversy` is deliberately excluded from the "7 phần" count in this
    task's AC1 — the prompt itself instructs `null` when sources agree
    ("KHÔNG bịa tranh cãi nếu các nguồn đồng thuận"), so it's an 8th,
    conditional field layered on top of the 7 mandatory ones (hook,
    introduction, problem, solution, demo, conclusion, cta).
    """

    hook: str
    introduction: str
    problem: str
    controversy: str | None = None
    solution: str
    demo: str
    conclusion: str
    cta: str


class OutlineContent(BaseModel):
    outline: OutlineSections
    warnings: list[ContentWarning] = Field(default_factory=list)


class ScriptContent(BaseModel):
    """`script.generate` output (docs/specs/prompts.md §6).

    `source_outline_version` is the cross-step lineage pointer AC5 needs —
    it is *not* the same thing as `StepVersion.parent_version` (that field
    tracks intra-step lineage only, e.g. script v2's parent script v1 after
    a restore; see app/services/versioning_service.py). Recording which
    outline version this script was generated from has to live inside the
    script's own content because the DB row has no cross-step FK for it.
    """

    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    voice_over: str
    estimated_duration_s: int
    source_outline_version: int | None = None
    warnings: list[ContentWarning] = Field(default_factory=list)
