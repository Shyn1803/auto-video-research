/**
 * SceneSidebar — column 1 of the Phân cảnh 3-column layout.
 *
 * Task 5-4: drag-and-drop reorder (dnd-kit) + ↑/↓ keyboard-equivalent
 * buttons on every row (AC-4 — every op must be doable without a mouse,
 * so the buttons are not merely a fallback, they're a first-class path);
 * add/duplicate/delete wired the same way.
 *
 * BR-1: reorder/move only ever changes `order` (→ scene_number); `id`
 * (→ scene_id) is always preserved — see sceneOpsReducer.
 * BR-2: delete confirms with the impact before removing.
 * BR-3: every op is meant to land a new scene_set version server-side.
 */

"use client";

import { useCallback, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useWorkspace, type SceneRow } from "@/lib/workspace-context";
import { StatusBadge } from "@/components/ui/status-badge";
import { moveScene, reorderScenes, deleteScene } from "@/lib/state/sceneOpsReducer";
import { reorderScenesApi, deleteSceneApi } from "@/lib/api/scenes";
import { LAYOUT_ICONS } from "@/components/workspace/LayoutPickerMenu";
import { AddSceneButton } from "@/components/workspace/AddSceneButton";
import { DuplicateSceneButton } from "@/components/workspace/DuplicateSceneButton";
import { DeleteSceneDialog } from "@/components/workspace/DeleteSceneDialog";

interface RowProps {
  scene: SceneRow;
  index: number;
  total: number;
  selected: boolean;
  onSelect: () => void;
  onMove: (direction: -1 | 1) => void;
  onRequestDelete: () => void;
}

function SceneRowItem({ scene, index, total, selected, onSelect, onMove, onRequestDelete }: RowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: scene.id,
  });
  const icon = LAYOUT_ICONS[scene.layoutClass] ?? "▣";

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`rounded-lg border ${
        selected ? "border-primary bg-primary/10" : "border-border bg-card"
      } ${isDragging ? "opacity-60" : ""}`}
    >
      <div className="flex items-center gap-1 p-2">
        {/* drag handle — pointer-only; ↑/↓ buttons below are the keyboard path */}
        <span
          {...attributes}
          {...listeners}
          aria-hidden="true"
          className="cursor-grab select-none px-0.5 text-muted-foreground/60 active:cursor-grabbing"
          title="Kéo để sắp xếp"
        >
          ⠿
        </span>

        <button
          type="button"
          onClick={onSelect}
          className="min-w-0 flex-1 text-left text-sm"
          aria-current={selected ? "true" : undefined}
        >
          <div className="flex items-center gap-1">
            <span className="text-xs font-mono">{icon}</span>
            <span className="truncate">
              #{index + 1} {scene.title}
            </span>
          </div>
          <div className="mt-1">
            <StatusBadge
              kind={scene.approved ? "pass" : "warn"}
              label={scene.approved ? "✓" : "⚠ đang sửa"}
              className="!px-1.5 !py-0 !text-[10px]"
            />
          </div>
        </button>

        <div className="flex flex-col">
          <button
            type="button"
            aria-label={`Chuyển cảnh ${index + 1} lên trên`}
            disabled={index === 0}
            onClick={() => onMove(-1)}
            className="rounded px-1 text-xs leading-none text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            ↑
          </button>
          <button
            type="button"
            aria-label={`Chuyển cảnh ${index + 1} xuống dưới`}
            disabled={index === total - 1}
            onClick={() => onMove(1)}
            className="rounded px-1 text-xs leading-none text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            ↓
          </button>
        </div>

        <div className="flex flex-col gap-0.5">
          <DuplicateSceneButton sceneId={scene.id} />
          <button
            type="button"
            aria-label={`Xoá cảnh ${index + 1}`}
            onClick={onRequestDelete}
            className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-status-fail"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

export function SceneSidebar() {
  const { state, dispatch } = useWorkspace();
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const persistAndSet = useCallback(
    (next: SceneRow[]) => {
      dispatch({ type: "SET_SCENES", scenes: next });
      reorderScenesApi(
        state.projectId,
        next.map((s) => s.id),
      ).catch(() => {
        // Best-effort — API failure surfaces via the normal save-status path
        // on next autosave tick; a hard rollback here would fight a concurrent
        // edit. Logged so provider_failover-style visibility isn't silently lost.
        console.error("[SceneSidebar] reorder persist failed");
      });
    },
    [dispatch, state.projectId],
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const fromIndex = state.scenes.findIndex((s) => s.id === active.id);
      const toIndex = state.scenes.findIndex((s) => s.id === over.id);
      if (fromIndex === -1 || toIndex === -1) return;
      persistAndSet(reorderScenes(state.scenes, fromIndex, toIndex));
    },
    [state.scenes, persistAndSet],
  );

  const handleMove = useCallback(
    (index: number, direction: -1 | 1) => {
      persistAndSet(moveScene(state.scenes, index, direction));
    },
    [state.scenes, persistAndSet],
  );

  const deleteTarget = state.scenes.find((s) => s.id === deleteTargetId);

  const handleConfirmDelete = useCallback(() => {
    if (!deleteTargetId) return;
    const deletedIndex = state.scenes.findIndex((s) => s.id === deleteTargetId);
    const next = deleteScene(state.scenes, deleteTargetId);
    dispatch({ type: "SET_SCENES", scenes: next });

    // AC-2 (biên): focus moves to the next scene; if the deleted scene was
    // last, fall back to the new last scene; empty → null (empty state).
    if (next.length === 0) {
      dispatch({ type: "SELECT_SCENE", index: null });
    } else {
      const nextIndex = Math.min(deletedIndex, next.length - 1);
      dispatch({ type: "SELECT_SCENE", index: nextIndex });
    }

    deleteSceneApi(state.projectId, deleteTargetId).catch(() => {
      console.error("[SceneSidebar] delete persist failed");
    });

    setDeleteTargetId(null);
  }, [deleteTargetId, dispatch, state.projectId, state.scenes]);

  return (
    <aside className="w-56 shrink-0 space-y-2" aria-label="Danh sách phân cảnh">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={state.scenes.map((s) => s.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {state.scenes.map((sc, idx) => (
              <SceneRowItem
                key={sc.id}
                scene={sc}
                index={idx}
                total={state.scenes.length}
                selected={state.selectedSceneIndex === idx}
                onSelect={() => dispatch({ type: "SELECT_SCENE", index: idx })}
                onMove={(direction) => handleMove(idx, direction)}
                onRequestDelete={() => setDeleteTargetId(sc.id)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {state.scenes.length === 0 && (
        <p className="rounded-lg border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
          Chưa có cảnh nào — thêm cảnh mới hoặc chạy lại storyboard.
        </p>
      )}

      <AddSceneButton />

      <p className="px-1 text-[11px] leading-tight text-muted-foreground/70">
        kéo-thả sắp xếp · <kbd className="rounded border border-border px-1">↑</kbd>
        <kbd className="ml-1 rounded border border-border px-1">↓</kbd>
      </p>

      <DeleteSceneDialog
        open={deleteTargetId !== null}
        scene={deleteTarget}
        onCancel={() => setDeleteTargetId(null)}
        onConfirm={handleConfirmDelete}
      />
    </aside>
  );
}
