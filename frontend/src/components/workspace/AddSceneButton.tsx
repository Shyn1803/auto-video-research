/**
 * AddSceneButton — Task 5-4 Step 3.
 *
 * "+" control that opens LayoutPickerMenu and inserts the new scene
 * immediately after the currently-open scene (or at the end if none is
 * selected). Calls the reducer (optimistic) then the API (server mints the
 * real scene_id + new scene_set version, BR-3).
 */

"use client";

import { useCallback, useRef, useState } from "react";
import { useWorkspace } from "@/lib/workspace-context";
import { addScene } from "@/lib/state/sceneOpsReducer";
import { addSceneApi } from "@/lib/api/scenes";
import { LayoutPickerMenu, type LayoutClass } from "@/components/workspace/LayoutPickerMenu";

export interface AddSceneButtonProps {
  /** Called after the scene has been optimistically inserted, with its (local) id. */
  onAdded?: (sceneId: string) => void;
}

export function AddSceneButton({ onAdded }: AddSceneButtonProps) {
  const { state, dispatch } = useWorkspace();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const handleSelect = useCallback(
    (layout: LayoutClass) => {
      setOpen(false);
      const afterIndex = state.selectedSceneIndex ?? state.scenes.length - 1;
      const next = addScene(state.scenes, afterIndex, {
        title: "Cảnh mới",
        layoutClass: layout,
      });
      dispatch({ type: "SET_SCENES", scenes: next });
      const insertedIdx = Math.min(Math.max(afterIndex + 1, 0), next.length - 1);
      const inserted = next[insertedIdx];
      dispatch({ type: "SELECT_SCENE", index: insertedIdx });

      addSceneApi(state.projectId, afterIndex + 1, layout)
        .then(() => onAdded?.(inserted.id))
        .catch(() => {
          console.error("[AddSceneButton] add scene persist failed");
        });

      triggerRef.current?.focus();
    },
    [dispatch, state.projectId, state.scenes, state.selectedSceneIndex, onAdded],
  );

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex w-full items-center justify-center rounded-lg border border-dashed border-border p-2 text-xs text-muted-foreground hover:border-primary hover:text-primary"
      >
        + Thêm cảnh
      </button>
      {open && (
        <LayoutPickerMenu onSelect={handleSelect} onClose={() => setOpen(false)} />
      )}
    </div>
  );
}
