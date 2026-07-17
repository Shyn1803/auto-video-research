/**
 * sceneOpsReducer tests — Task 5-4 Step 1.
 *
 * Co-located under src/lib/state/__tests__ (not the task file's literal
 * frontend/tests/unit/state path) because vitest.config.ts's
 * `include: ['src/**\/*.test.{ts,tsx}']` only picks up co-located tests —
 * matches the existing PipelineStepper.test.tsx convention already in this repo.
 */

import { describe, expect, it } from "vitest";
import type { SceneRow } from "@/lib/workspace-context";
import {
  addScene,
  deleteScene,
  deleteImpactMessage,
  duplicateScene,
  moveScene,
  reorderScenes,
} from "../sceneOpsReducer";

function makeScenes(n: number): SceneRow[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `s${i + 1}`,
    title: `Cảnh ${i + 1}`,
    order: i,
    approved: i % 2 === 0,
    warnings: [],
    layoutClass: "Hero",
  }));
}

describe("sceneOpsReducer", () => {
  it("reorder: moving #4 (index 3) to position 2 (index 1) preserves every id, renumbers order", () => {
    const scenes = makeScenes(5);
    const next = reorderScenes(scenes, 3, 1);
    // ids preserved as a set
    expect(next.map((s) => s.id).sort()).toEqual(scenes.map((s) => s.id).sort());
    // moved scene is now at index 1
    expect(next[1].id).toBe("s4");
    // order is 0..n-1 contiguous
    expect(next.map((s) => s.order)).toEqual([0, 1, 2, 3, 4]);
  });

  it("reorder: no-op when indexes are equal or out of range", () => {
    const scenes = makeScenes(3);
    expect(reorderScenes(scenes, 1, 1)).toBe(scenes);
    expect(reorderScenes(scenes, -1, 1)).toBe(scenes);
    expect(reorderScenes(scenes, 0, 9)).toBe(scenes);
  });

  it("moveScene: keyboard up/down is equivalent to a 1-step reorder", () => {
    const scenes = makeScenes(4);
    const down = moveScene(scenes, 0, 1);
    expect(down[1].id).toBe("s1");
    const up = moveScene(down, 1, -1);
    expect(up.map((s) => s.id)).toEqual(scenes.map((s) => s.id));
  });

  it("addScene: inserts a new scene immediately after the given index with a new id", () => {
    const scenes = makeScenes(3);
    const next = addScene(scenes, 0, { title: "Mới", layoutClass: "TextFocus" });
    expect(next).toHaveLength(4);
    expect(next[1].title).toBe("Mới");
    expect(next[1].layoutClass).toBe("TextFocus");
    expect(scenes.every((s) => s.id !== next[1].id)).toBe(true);
    expect(next.map((s) => s.order)).toEqual([0, 1, 2, 3]);
  });

  it("deleteScene: removes the scene and renumbers order", () => {
    const scenes = makeScenes(3);
    const next = deleteScene(scenes, "s2");
    expect(next.map((s) => s.id)).toEqual(["s1", "s3"]);
    expect(next.map((s) => s.order)).toEqual([0, 1]);
  });

  it("deleteScene: deleting every scene yields an empty array (empty state)", () => {
    let scenes = makeScenes(2);
    scenes = deleteScene(scenes, "s1");
    scenes = deleteScene(scenes, "s2");
    expect(scenes).toEqual([]);
  });

  it("BR-4 duplicateScene: copy gets a new id, original content copied, inserted right after original", () => {
    const scenes = makeScenes(3);
    const next = duplicateScene(scenes, "s2");
    expect(next).toHaveLength(4);
    const original = next.find((s) => s.id === "s2")!;
    const copyIdx = next.findIndex((s) => s.id === "s2") + 1;
    const copy = next[copyIdx];
    expect(copy.id).not.toBe("s2");
    expect(copy.title).toBe(original.title);
    expect(copy.layoutClass).toBe(original.layoutClass);
  });

  it("BR-4: editing the duplicate does not mutate the original (independent objects)", () => {
    const scenes = makeScenes(2);
    const next = duplicateScene(scenes, "s1");
    const copyIdx = next.findIndex((s) => s.id === "s1") + 1;
    const edited = next.map((s, i) => (i === copyIdx ? { ...s, title: "Sửa bản sao" } : s));
    const original = edited.find((s) => s.id === "s1")!;
    expect(original.title).toBe("Cảnh 1");
    expect(edited[copyIdx].title).toBe("Sửa bản sao");
  });

  it("BR-2 deleteImpactMessage: states the impact in seconds", () => {
    const scenes = makeScenes(1);
    expect(deleteImpactMessage(scenes[0], 6000)).toContain("6s");
  });
});
