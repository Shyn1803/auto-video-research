/**
 * sceneDiff — formats the backend's `{type:"scene_set", added[], removed[],
 * changed:[{scene_id, fields[]}]}` compare response (storyboard/scene_set
 * steps) into a single renderable list.
 *
 * BR-4 (a11y): each entry carries an explicit `prefix` — a consumer must
 * render it alongside color, never color alone.
 */

export interface SceneDiffChanged {
  scene_id: string;
  fields: string[];
}

export type SceneDiffKind = "added" | "removed" | "changed";

export interface SceneDiffEntry {
  kind: SceneDiffKind;
  sceneId: string;
  prefix: "+" | "-" | "~";
  fields?: string[];
}

export function buildSceneDiffList(
  added: string[] = [],
  removed: string[] = [],
  changed: SceneDiffChanged[] = [],
): SceneDiffEntry[] {
  return [
    ...added.map((sceneId): SceneDiffEntry => ({ kind: "added", sceneId, prefix: "+" })),
    ...removed.map((sceneId): SceneDiffEntry => ({ kind: "removed", sceneId, prefix: "-" })),
    ...changed.map(
      (c): SceneDiffEntry => ({
        kind: "changed",
        sceneId: c.scene_id,
        prefix: "~",
        fields: c.fields,
      }),
    ),
  ];
}
