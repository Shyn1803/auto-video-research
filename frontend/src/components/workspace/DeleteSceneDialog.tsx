/**
 * DeleteSceneDialog — Task 5-4 Step 4.
 *
 * BR-2: states the impact ("video ngắn đi ~6s") before the user confirms.
 * Focus-trap defaults to the safe (Huỷ/cancel) button — a11y AC-4, and it
 * keeps an accidental Enter-key press from deleting a scene.
 *
 * Deleting the currently-open scene moves selection to the next scene (or
 * the previous one if the deleted scene was last); deleting the last scene
 * leaves the empty state to the caller (selectedSceneIndex = null).
 */

"use client";

import { useEffect, useRef } from "react";
import type { SceneRow } from "@/lib/workspace-context";
import { deleteImpactMessage } from "@/lib/state/sceneOpsReducer";

export interface DeleteSceneDialogProps {
  open: boolean;
  scene: SceneRow | undefined;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteSceneDialog({ open, scene, onCancel, onConfirm }: DeleteSceneDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label="Xác nhận xoá cảnh"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onKeyDown={(e) => {
        if (e.key === "Escape") onCancel();
      }}
    >
      <div className="w-80 rounded-xl border border-border bg-card p-4 shadow-xl">
        <h3 className="text-sm font-semibold text-foreground">Xoá cảnh này?</h3>
        <p className="mt-2 text-sm text-muted-foreground">{deleteImpactMessage(scene)}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Huỷ
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-status-fail px-3 py-1.5 text-sm font-medium text-white hover:brightness-110"
          >
            Xoá
          </button>
        </div>
      </div>
    </div>
  );
}
