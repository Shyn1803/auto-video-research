"""Storyboard node — Step 1 of 4-6 + 4-5 wiring.

Calls LLM once to produce the Semantic Storyboard (Scene Tree).
Layout decisions are NEVER in the LLM output — see scene_tree.py BR-1.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.adapters.registry import get_adapter
from app.pipeline.nodes.base import complete_node
from app.pipeline.state import NodeName, PipelineState
from app.schemas.scene_tree import SemanticStoryboard, SceneTreeScene
from app.services.prompt_render import get_active_prompt, render

logger = logging.getLogger("avr.storyboard.generate")

_STORYBOARD_ZERO_SHOT = """\
Bạn là biên tập viên kịch bản video ngắn tiếng Việt. Nhiệm vụ: bóc tách
kịch bản thành các cảnh phân đoạn, mô tả ý đồ nội dung mỗi cảnh — KHÔNG chọn layout.

Quy tắc cứng:
1. Chỉ dùng 10 component kind: heading, body, media_intent, stat, bullet,
   chart_data, table_data, quote, code, group.
2. Mỗi scene: 1-8 components; bullet ≤6 items; group ≤2 mức.
3. Mỗi component có narration_anchor (chuỗi con nguyên văn 20-80 ký tự của narration_text).
4. KHÔNG sinh field layout/vị trí/font/animation/camera/transition — hệ thống sẽ tự quyết.
5. narration_text PHẢI khớp hoàn toàn voice_over của scene (BR-2).

Output JSON duy nhất — không giải thích thêm:
{schema_hint}
"""


def _schema_hint() -> str:
    return (
        '{"scenes": [{"scene_number": 1, "narration_text": "…", '
        '"narration_anchor": "…", "purpose": "intro|context|evidence|…", '
        '"components": [{"kind": "heading", "summary": "…", '
        '"narration_anchor": "…", "content": {}, '
        '"media_query_vi": "…", "media_hint": "photo|footage", '
        '"source_id": "…"}]}], "total_duration_s": 60.0}'
    )


async def generate_semantic_storyboard(
    session: Any,
    *,
    script: dict[str, Any],
    topic: str,
    target_duration_s: float = 60.0,
    router: Any | None = None,
    correlation_id: str = "",
) -> SemanticStoryboard:
    """Call LLM to produce a Scene Tree from the script (write node output).

    Returns on success; raises on schema mismatch (BR-1) or LLM failure.
    """
    prompt_version = await get_active_prompt(session, "storyboard.generate")
    if prompt_version is None:
        # Fall back to zero-shot when no seeded prompt is active yet (MM-1 dev)
        template = _STORYBOARD_ZERO_SHOT.format(schema_hint=_schema_hint())
        prompt_vars: dict[str, Any] = {
            "script_vi": script.get("script_vi", ""),
            "outline_sections": script.get("outline_sections", []),
            "target_duration_s": target_duration_s,
            "today": __import__("datetime").date.today().isoformat(),
        }
    else:
        template = render(prompt_version.template, {
            "script_vi": script.get("script_vi", ""),
            "outline_sections": script.get("outline_sections", []),
            "target_duration_s": target_duration_s,
            "today": __import__("datetime").date.today().isoformat(),
            "schema_hint": _schema_hint(),
        })
        prompt_vars = {}

    if router is None:
        from app.adapters.registry import _registry
        router = _registry

    llm_name, llm_cls = next(iter(router.items()))
    adapter = llm_cls(router.get(llm_name, {}).get("settings") if isinstance(router, dict) else None)
    if hasattr(adapter, "available") and not adapter.available():
        raise RuntimeError(f"No LLM provider available for storyboard node")

    raw = await adapter.call(template, prompt_vars if prompt_vars else None)

    try:
        raw_dict = json.loads(raw) if isinstance(raw, str) else raw
        return SemanticStoryboard.model_validate(raw_dict)
    except Exception as exc:
        logger.error(
            "storyboard parse fail run=%s: %s", correlation_id, exc, exc_info=True
        )
        raise ValueError(f"Semantic Storyboard schema violation (BR-1): {exc}") from exc


async def run_storyboard(
    session: Any,
    state: PipelineState,
    *,
    router: Any | None = None,
    project: Any | None = None,
) -> PipelineState:
    """LangGraph node entry point — produces semantic_tree in state.

    Step 1 only: AI call → Scene Tree. All downstream passes are pure
    functions over this tree (Layout Engine).
    """
    project_id = state.project_id
    run_id = state.run_id

    write_out = state.write
    script = {
        "script_vi": write_out.get("script", {}).get("script_vi", ""),
        "outline_sections": write_out.get("outline", {}).get("sections", []),
    }
    target_duration_s = state.write.get("target_duration_s", 60.0)

    logger.info(
        "storyboard start project=%s run=%s", project_id, run_id,
        extra={"correlation_id": run_id},
    )

    tree = await generate_semantic_storyboard(
        session,
        script=script,
        topic=state.write.get("topic", ""),
        target_duration_s=target_duration_s,
        router=router,
        correlation_id=run_id,
    )

    state.storyboard["semantic_tree"] = tree.model_dump(mode="json")
    state.completed_nodes.append(NodeName.STORYBOARD)

    run_updates: dict[str, Any] = {"current_node": NodeName.STORYBOARD.value}

    if project is not None:
        await complete_node(
            session,
            project_id=project_id,
            node=NodeName.STORYBOARD,
            content=state.storyboard,
            actor="pipeline",
            run=project.run if hasattr(project, "run") else None,
            run_updates=run_updates,
        )
    logger.info(
        "storyboard done project=%s scenes=%d", project_id, len(tree.scenes),
        extra={"correlation_id": run_id},
    )
    return state
