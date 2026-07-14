"""Mock LLM adapter — deterministic fixtures keyed by ``prompt_name``.

Hard guard: raises at ``available()`` and ``call_structured()`` call time
if ``APP_ENV=production`` and the adapter is present in the resolved chain
(BR-2). The router's startup validation must also refuse ``mock`` in
production chains.

Only active when ``APP_ENV`` is ``development`` or ``test``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.adapters.base import LLMAdapter, ProviderError, ProviderSettings
from app.adapters.registry import register_llm

logger = logging.getLogger("avr.llm.mock")

# Deterministic fixture responses keyed by prompt-keyword.
_FIXTURES: dict[str, dict[str, Any]] = {
    "summarize": {
        "summary": "Tóm tắt: nội dung chính là về chủ đề AI và tự động hóa.",
        "key_points": ["AI", "tự động hóa", "nội dung"],
        "sentiment": "neutral",
        "word_count_estimate": 120,
    },
    "fact_check": {
        "claims": [
            {"claim": "AI improves productivity", "verdict": "PASS", "sources_used": 2},
            {"claim": "AI causes job loss", "verdict": "WARN", "sources_used": 2},
        ],
        "overall_pass": True,
        "notes": "Mixed signals require human review.",
    },
    "script": {
        "scenes": [
            {
                "scene_id": 1,
                "layout_class": "Hero",
                "component_kind": "heading",
                "text": "AI đang thay đổi thế giới",
                "duration_s": 5,
            },
            {
                "scene_id": 2,
                "layout_class": "TextFocus",
                "component_kind": "body",
                "text": "Tự động hóa là xu hướng số 1.",
                "duration_s": 4,
            },
        ],
        "total_duration_s": 20,
        "tts_tier": "cheap",
    },
    "storyboard": {
        "scenes": [
            {"scene_id": 1, "layout_class": "Hero"},
            {"scene_id": 2, "layout_class": "TextFocus"},
            {"scene_id": 3, "layout_class": "MediaText"},
        ]
    },
}


@register_llm("mock")
class MockLLM(LLMAdapter):
    name: str = "mock"
    is_paid: bool = False

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        super().__init__(settings)
        self._env: str = os.environ.get("APP_ENV", "development")

    # ------------------------------------------------------------------
    # available()
    # ------------------------------------------------------------------

    async def available(self) -> bool:
        self._production_guard()
        return True

    # ------------------------------------------------------------------
    # call_structured()
    # ------------------------------------------------------------------

    async def call_structured(
        self,
        prompt: str,
        schema: dict[str, object],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        tier: str = "cheap",
    ) -> dict[str, object]:
        self._production_guard()

        fixture = self._resolve_fixture(prompt)
        if fixture is not None:
            return fixture
        return _build_stub(schema)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _production_guard(self) -> None:
        if self._env == "production":
            raise ProviderError(
                "mock adapter: not available in APP_ENV=production",
                retryable=False,
            )

    @staticmethod
    def _resolve_fixture(prompt: str) -> dict[str, Any] | None:
        prompt_lower = prompt.lower()
        for key, fixture in _FIXTURES.items():
            if key in prompt_lower:
                logger.debug(
                    "mock: matched fixture %r (prompt=%r)",
                    key,
                    prompt[:100],
                )
                return fixture
        return None


def _build_stub(schema: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key in schema:
        key_def = schema[key]
        if isinstance(key_def, dict):
            ftype = key_def.get("type", "string")
            if ftype == "number":
                out[key] = 42.0
            elif ftype == "integer":
                out[key] = 42
            elif ftype == "boolean":
                out[key] = True
            elif ftype == "array":
                out[key] = []
            else:
                out[key] = f"[mock:{key}]"
        else:
            out[key] = f"[mock:{key}]"
    return out
