/**
 * StaleConfirmDialog — BR-1 "Sửa lại từ đây" confirmation.
 *
 * Clicking a done station's "Sửa lại từ đây" button must first show a
 * confirm dialog listing which later steps will become stale (per BR-1:
 * "confirm liệt kê bước sẽ stale"), before actually unlocking edit mode.
 * Only on confirm does it: (1) unlock readonly, (2) mark every station
 * after the current one as stale-if-done (visually — the real
 * recompute/cascade of stale scene_set versions happens server-side once
 * 5-4/backend pipeline wiring lands; this dialog owns the UI confirmation
 * gate only).
 */

"use client";

import { useWorkspace, STATIONS, type StepStatus } from "@/lib/workspace-context";

export interface StaleConfirmDialogProps {
  open: boolean;
  /** index of the station being re-opened for edit */
  fromIndex: number;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Stations after `fromIndex` that are currently done (or done-warning) — these go stale. */
export function staleStationLabels(
  stationStates: StepStatus[],
  fromIndex: number,
): string[] {
  return STATIONS.filter((_, i) => i > fromIndex && stationStates[i]?.startsWith("done")).map(
    (s) => s.label,
  );
}

export function StaleConfirmDialog({
  open,
  fromIndex,
  onCancel,
  onConfirm,
}: StaleConfirmDialogProps) {
  const { state } = useWorkspace();

  if (!open) return null;

  const staleLabels = staleStationLabels(state.stationStates, fromIndex);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="alertdialog"
      aria-modal="true"
      aria-label="Xác nhận sửa lại từ đây"
    >
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-6">
        <h3 className="text-lg font-semibold text-foreground">Sửa lại từ đây?</h3>
        {staleLabels.length > 0 ? (
          <div className="text-sm text-muted-foreground">
            <p className="mb-1">Các bước sau sẽ trở thành lỗi thời (cần làm lại):</p>
            <ul className="list-disc space-y-0.5 pl-5">
              {staleLabels.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Không có bước nào phía sau bị ảnh hưởng.
          </p>
        )}
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
            Vào sửa
          </button>
        </div>
      </div>
    </div>
  );
}
