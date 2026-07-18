/**
 * Versions API client (task 5-9) — matches backend contract exactly
 * (app/schemas/version.py, docs/specs/api-spec.md §3, task 1-5).
 *
 * No generated OpenAPI client exists yet for non-admin routers in this repo
 * (frontend/src/lib/api/ only had interceptor.ts before this task) — these
 * types are hand-written against the real Pydantic schemas, not paraphrased
 * from the task file, per CLAUDE.md §5 "API types generated from OpenAPI"
 * intent (to reconcile once `make gen-api-client` exists for non-admin
 * routes).
 */

import { api } from "./interceptor";

export interface VersionOut {
  id: string;
  version: number;
  step: string;
  stale: boolean;
  parent_version: number | null;
  created_by: string;
  created_at: string;
}

export interface VersionListResponse {
  versions: VersionOut[];
}

export interface CurrentResponse {
  current: VersionOut;
  all_stale: boolean;
}

export interface RestoreResponse {
  restored: VersionOut;
  staled_steps: string[];
}

/** BR-4: type is "text" (outline/script) or "scene_set" (storyboard/scene_set) or "raw". */
export interface CompareResponse {
  type: "text" | "scene_set" | "raw";
  diff?: string | null;
  added?: string[] | null;
  removed?: string[] | null;
  changed?: { scene_id: string; fields: string[] }[] | null;
  v1_content?: Record<string, unknown> | null;
  v2_content?: Record<string, unknown> | null;
}

export async function listVersions(
  projectId: string,
  step: string,
): Promise<VersionListResponse> {
  const res = await api.get<VersionListResponse>(
    `/projects/${projectId}/steps/${step}/versions`,
  );
  return res.data;
}

/** Task 5-9 additive endpoint — VersionOut has no `content`; this is the
 * only way to view a past version's full content (used by the "Xem"
 * readonly overlay). See docs/specs/api-spec.md §3 contract change note. */
export interface VersionDetailOut extends VersionOut {
  content: Record<string, unknown>;
}

export async function getVersionDetail(
  projectId: string,
  step: string,
  version: number,
): Promise<VersionDetailOut> {
  const res = await api.get<VersionDetailOut>(
    `/projects/${projectId}/steps/${step}/versions/${version}`,
  );
  return res.data;
}

export async function getCurrentVersion(
  projectId: string,
  step: string,
): Promise<CurrentResponse> {
  const res = await api.get<CurrentResponse>(
    `/projects/${projectId}/steps/${step}/current`,
  );
  return res.data;
}

/** BR-1: the one restore path — 409 while project is running, 404 if version missing. */
export async function restoreVersion(
  projectId: string,
  step: string,
  version: number,
): Promise<RestoreResponse> {
  const res = await api.post<RestoreResponse>(
    `/projects/${projectId}/steps/${step}/versions/${version}/restore`,
  );
  return res.data;
}

export async function compareVersions(
  projectId: string,
  step: string,
  from: number,
  to: number,
): Promise<CompareResponse> {
  const res = await api.get<CompareResponse>(
    `/projects/${projectId}/steps/${step}/versions/compare`,
    { params: { from, to } },
  );
  return res.data;
}
