/**
 * DuplicateSceneButton — Task 5-4 Step 4.
 *
 * BR-4: the copy gets a brand-new scene_id (cache key differs); content is
 * copied so editing the copy afterwards never touches the original.
 */

"use client";

import { useCallback } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { duplicateScene } from "@/lib/state/sceneOpsReducer";
import { duplicateSceneApi } from "@/lib/api/scenes";

export interface DuplicateSceneButtonProps {
  sceneId: string;
  label?: string;
}

export function DuplicateSceneButton({ sceneId, label = "Nhân bản" }: DuplicateSceneButtonProps) {
  const { state, dispatch } = useWorkspace();

  const handleDuplicate = useCallback(() => {
    const next = duplicateScene(state.scenes, sceneId);
    if (next === state.scenes) return; // scene not found, no-op
    dispatch({ type: "SET_SCENES", scenes: next });
    const originalIdx = next.findIndex((s) => s.id === sceneId);
    const insertedIdx = originalIdx + 1;
    dispatch({ type: "SELECT_SCENE", index: insertedIdx });

    duplicateSceneApi(state.projectId, sceneId).catch(() => {
      console.error("[DuplicateSceneButton] duplicate persist failed");
    });
  }, [dispatch, sceneId, state.projectId, state.scenes]);

  return (
    <button
      type="button"
      onClick={handleDuplicate}
      aria-label={`${label} cảnh`}
      className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
    >
      ⧉
    </button>
  );
}
