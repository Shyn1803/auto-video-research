"""Pipeline state schema — Pydantic from day one.

Every node in the pipeline reads/writes fields from this model.
LangGraph serializes it for checkpointing; Pydantic enforces the contract.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class NodeName(StrEnum):
    RESEARCH = "research"
    RANKING = "ranking"
    WRITE = "write"
    FACTCHECK = "factcheck"
    STORYBOARD = "storyboard"
    PRODUCE = "produce"
    RENDER = "render"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineState(BaseModel):
    """Shared state passed through every pipeline node.

    Fields are additive — a node only reads/writes its own output key.
    """

    project_id: str = Field(..., description="UUID of the project being processed")
    run_id: str = Field(..., description="Correlation ID for this pipeline run")
    current_node: NodeName | None = None
    completed_nodes: list[NodeName] = Field(default_factory=list)
    status: RunStatus = RunStatus.PENDING

    # Entry routing: set by entry_router_node, consumed by conditional edges.
    # Values: "research" (default) or "script".
    entry_point: str = Field(
        default="research",
        description="Which pipeline entry to use: 'research' or 'script'.",
    )

    # Node outputs — each node writes its section
    research: dict[str, Any] = Field(default_factory=dict)
    ranking: dict[str, Any] = Field(default_factory=dict)
    write: dict[str, Any] = Field(default_factory=dict)
    factcheck: dict[str, Any] = Field(default_factory=dict)
    storyboard: dict[str, Any] = Field(default_factory=dict)
    produce: dict[str, Any] = Field(default_factory=dict)
    render: dict[str, Any] = Field(default_factory=dict)

    # Control
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    human_gate_required: bool = False
    approved: bool = False
