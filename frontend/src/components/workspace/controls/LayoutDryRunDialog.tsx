/**
 * LayoutDryRunDialog — task 5-2 Step 4, BR-1.
 *
 * Before a layout change is committed, `checkLayoutChange`
 * (lib/scene/layout-constraints.ts) validates the target layout's element
 * constraints against the scene's current texts/images. On violation this
 * dialog names the exact elements that would be dropped (BR-1: "dialog liệt
 * kê đích danh phần tử bị bỏ"). Cancel restores the prior selection exactly
 * — this component never mutates the caller's layout state itself, it only
 * reports the dry-run result and lets the caller decide.
 */

"use client";

import { checkLayoutChange, type DryRunTextLike } from "@/lib/scene/layout-constraints";

export interface LayoutDryRunDialogProps {
  open: boolean;
  fromLayout: string;
  toLayout: string;
  texts: DryRunTextLike[];
  imagesCount: number;
  onCancel: () => void;
  onConfirm: () => void;
}

export function LayoutDryRunDialog({
  open,
  fromLayout,
  toLayout,
  texts,
  imagesCount,
  onCancel,
  onConfirm,
}: LayoutDryRunDialogProps) {
  if (!open) return null;

  const result = checkLayoutChange(texts, imagesCount, toLayout);

  // No violation — nothing to warn about, caller shouldn't have opened this,
  // but render nothing rather than a confusing empty dialog.
  if (result.ok) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="alertdialog"
      aria-modal="true"
      aria-label="Xác nhận đổi bố cục"
    >
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-6">
        <h3 className="text-lg font-semibold text-foreground">
          Đổi bố cục {fromLayout} → {toLayout}?
        </h3>

        <div className="text-sm text-muted-foreground">
          <p className="mb-1">Bố cục mới không chứa đủ chỗ cho mọi phần tử hiện có:</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {result.droppedTextExcerpts.map(({ id, excerpt }) => (
              <li key={id}>
                chữ &apos;{id}&apos; sẽ bị bỏ — &quot;{excerpt}
                {excerpt.length >= 24 ? "…" : ""}&quot;
              </li>
            ))}
            {result.imagesExceed && (
              <li>
                {result.imagesCount} ảnh vượt quá giới hạn {result.imagesMax} ảnh của {toLayout} —
                ảnh dư sẽ bị bỏ
              </li>
            )}
          </ul>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:brightness-110"
          >
            Vẫn đổi
          </button>
        </div>
      </div>
    </div>
  );
}
