/**
 * sceneOpsReducer — pure functions for the 4 scene ops (Task 5-4).
 *
 * BR-1: reorder only ever changes `order` (→ scene_number on the backend);
 *       `id` (→ scene_id) is never touched — this is what keeps cache/diff
 *       correct across a reorder (see patterns/scene-versioning.md).
 * BR-3: every op is meant to produce a new scene_set version server-side —
 *       there is no separate undo stack in the editor (locked decision).
 * BR-4: duplicate mints a brand-new scene_id with copied content, so the
 *       copy's cache key differs from the original's.
 *
 * These functions are UI-local (optimistic) mirrors of the server-side
 * scene_service.py ops — the real version-producing mutation happens via
 * the API; this reducer keeps local state consistent between round trips
 * and is unit-testable without a backend.
 */

import type { SceneRow } from "@/lib/workspace-context";

let localIdCounter = 0;

/** Generate a client-local id for optimistic inserts (server assigns the
 * real scene_id on the API round trip; this is only ever a placeholder). */
export function newLocalSceneId(): string {
  localIdCounter += 1;
  return `local-${Date.now()}-${localIdCounter}`;
}

/** Renumber `order` 0..n-1, preserving every `id`. */
function renumber(scenes: SceneRow[]): SceneRow[] {
  return scenes.map((s, idx) => ({ ...s, order: idx }));
}

/**
 * Move the scene at `fromIndex` to `toIndex`. Only `order` changes for any
 * scene — every `id` is preserved (BR-1).
 */
export function reorderScenes(
  scenes: SceneRow[],
  fromIndex: number,
  toIndex: number,
): SceneRow[] {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= scenes.length ||
    toIndex >= scenes.length
  ) {
    return scenes;
  }
  const next = [...scenes];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return renumber(next);
}

/** Move a scene up (-1) or down (+1) by one position — keyboard-equivalent. */
export function moveScene(scenes: SceneRow[], index: number, direction: -1 | 1): SceneRow[] {
  return reorderScenes(scenes, index, index + direction);
}

export interface NewSceneTemplate {
  title: string;
  layoutClass: string;
}

/** Insert a new empty scene immediately after `afterIndex` (-1 = at the start). */
export function addScene(
  scenes: SceneRow[],
  afterIndex: number,
  template: NewSceneTemplate,
): SceneRow[] {
  const next = [...scenes];
  const insertAt = Math.min(Math.max(afterIndex + 1, 0), next.length);
  const created: SceneRow = {
    id: newLocalSceneId(),
    title: template.title,
    order: insertAt,
    approved: false,
    warnings: [],
    layoutClass: template.layoutClass,
  };
  next.splice(insertAt, 0, created);
  return renumber(next);
}

/** Remove a scene by id. */
export function deleteScene(scenes: SceneRow[], id: string): SceneRow[] {
  const next = scenes.filter((s) => s.id !== id);
  return renumber(next);
}

/**
 * Duplicate a scene: the copy gets a brand-new `id` (BR-4) with the same
 * content otherwise, inserted immediately after the original.
 */
export function duplicateScene(scenes: SceneRow[], id: string): SceneRow[] {
  const idx = scenes.findIndex((s) => s.id === id);
  if (idx === -1) return scenes;
  const original = scenes[idx];
  const copy: SceneRow = {
    ...original,
    id: newLocalSceneId(),
  };
  const next = [...scenes];
  next.splice(idx + 1, 0, copy);
  return renumber(next);
}

/** BR-2 helper: human-readable impact statement for a delete confirm dialog. */
export function deleteImpactMessage(
  scene: SceneRow | undefined,
  estimatedSceneMs = 6000,
): string {
  const seconds = Math.round(estimatedSceneMs / 1000);
  if (!scene) return `Video sẽ ngắn đi khoảng ${seconds}s`;
  return `Xoá cảnh "${scene.title}" — video ngắn đi khoảng ${seconds}s`;
}
