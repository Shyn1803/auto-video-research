"""Schemas for versioning API (task 1-5, api-spec §3)."""

from __future__ import annotations

from pydantic import BaseModel


class VersionOut(BaseModel):
    id: str
    version: int
    step: str
    stale: bool
    parent_version: int | None
    created_by: str
    created_at: str


class VersionListResponse(BaseModel):
    versions: list[VersionOut]


class VersionDetailOut(VersionOut):
    """Task 5-9: additive detail response for the readonly 'Xem' overlay.

    ``VersionOut`` (list/current/restore) deliberately omits ``content`` to
    keep the list endpoint's payload small. Comparing two versions only ever
    returns a diff/scene-diff for the four content-bearing steps (never the
    raw content) — there was no existing way to view one past version's full
    content, which 5-9's "Xem" AC needs. Purely additive (new endpoint, no
    existing response shape changed) — see docs/specs/api-spec.md §3.
    """

    content: dict


class VersionCreate(BaseModel):
    content: dict
    parent_version: int | None = None
    actor: str | None = None


class CurrentResponse(BaseModel):
    current: VersionOut
    all_stale: bool


class RestoreResponse(BaseModel):
    restored: VersionOut
    staled_steps: list[str]


class CompareRequest(BaseModel):
    v1: int
    v2: int


class CompareResponse(BaseModel):
    type: str
    diff: str | None = None
    added: list[str] | None = None
    removed: list[str] | None = None
    changed: list[dict] | None = None
    v1_content: dict | None = None
    v2_content: dict | None = None
