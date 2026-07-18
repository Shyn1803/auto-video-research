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
