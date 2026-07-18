/**
 * VersionRestoreDialog — task 5-9 "Khôi phục".
 *
 * BR-1: restore goes through the single 1-5 `VersioningService.restore()`
 * path exclusively (via lib/api/versions.ts `restoreVersion`) — no parallel
 * restore logic lives in this component.
 * AC-2: confirm states the consequence ("Hoàn thiện sẽ lỗi thời") by
 * predicting, client-side, which Stations sit downstream of this version's
 * step (STATIONS order is fixed — same technique StaleConfirmDialog already
 * uses for the "Sửa lại từ đây" flow). The actual visual stale-cascade is
 * only ever applied from the real `staled_steps` the restore response
 * returns (source of truth), never from this client-side prediction.
 * AC-5: restore is disabled with a tooltip while `project.status === "running"`.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { STATIONS, stationIndexForVersioningStep, type SaveStatus } from "@/lib/workspace-context";
import { restoreVersion, type VersionOut } from "@/lib/api/versions";

export interface VersionRestoreDialogProps {
  projectId: string;
  step: string;
  version: VersionOut;
  /** WorkspaceState.projectStatus — "running" disables restore (AC-5). */
  projectStatus: string;
  /** WorkspaceState.saveStatus/unsavedChanges — BR-2/AC-3: an in-flight
   * autosave defers the switch until it completes, never discarding the
   * edit. Optional so existing/isolated tests don't need to pass them. */
  saveStatus?: SaveStatus;
  unsavedChanges?: boolean;
  onClose: () => void;
  onRestored: (staledSteps: string[]) => void;
}

export default function VersionRestoreDialog({
  projectId,
  step,
  version,
  projectStatus,
  saveStatus = "saved",
  unsavedChanges = false,
  onClose,
  onRestored,
}: VersionRestoreDialogProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // BR-2/AC-3: user confirmed while a save was still in flight — the actual
  // restore call is held back until saveStatus flips away from "saving"
  // rather than firing immediately and racing an unsaved edit.
  const [awaitingSave, setAwaitingSave] = useState(false);
  const awaitingSaveRef = useRef(false);

  const running = projectStatus === "running";
  const saving = saveStatus === "saving" || unsavedChanges;
  const fromIndex = stationIndexForVersioningStep(step);
  const affectedLabels = STATIONS.filter((_, i) => i > fromIndex).map((s) => s.label);

  async function doRestore() {
    setPending(true);
    setError(null);
    try {
      const res = await restoreVersion(projectId, step, version.version);
      onRestored(res.staled_steps);
    } catch (err) {
      const responseStatus = (err as { response?: { status?: number } })?.response?.status;
      if (responseStatus === 409) {
        setError("Không thể khôi phục khi dự án đang chạy.");
      } else if (responseStatus === 404) {
        setError("Phiên bản không tồn tại.");
      } else {
        setError("Khôi phục thất bại, thử lại sau.");
      }
    } finally {
      setPending(false);
    }
  }

  // Once the deferred save finishes, run the restore the user already
  // confirmed — no data is lost and no second click is required.
  useEffect(() => {
    if (awaitingSaveRef.current && !saving) {
      awaitingSaveRef.current = false;
      setAwaitingSave(false);
      void doRestore();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saving]);

  function handleConfirm() {
    // Deliberately aria-disabled, not the native `disabled` attribute (see
    // PipelineStepper.tsx's own comment) — guard here instead so the click
    // handler stays the single source of truth for "can this run right now".
    if (running || pending || awaitingSave) return;
    if (saving) {
      awaitingSaveRef.current = true;
      setAwaitingSave(true);
      return;
    }
    void doRestore();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="alertdialog"
      aria-modal="true"
      aria-label="Xác nhận khôi phục phiên bản"
    >
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-6">
        <h3 className="text-lg font-semibold text-foreground">Khôi phục v{version.version}?</h3>

        {affectedLabels.length > 0 ? (
          <div className="text-sm text-muted-foreground">
            <p className="mb-1">Hoàn thiện sẽ lỗi thời — các bước sau sẽ cần làm lại:</p>
            <ul className="list-disc space-y-0.5 pl-5">
              {affectedLabels.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Không có bước nào phía sau bị ảnh hưởng.</p>
        )}

        {error && <p className="text-sm text-status-fail">{error}</p>}
        {awaitingSave && (
          <p className="text-sm text-status-warn">
            Đang chờ lưu xong thay đổi hiện tại trước khi khôi phục…
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            aria-disabled={running || pending || undefined}
            title={running ? "Dự án đang chạy — không thể khôi phục" : undefined}
            className={`rounded-lg px-4 py-2 text-sm font-semibold text-primary-foreground ${
              running || pending
                ? "cursor-not-allowed bg-primary/40"
                : "bg-primary hover:brightness-110"
            }`}
          >
            {pending ? "Đang khôi phục…" : awaitingSave ? "Chờ lưu…" : "Khôi phục"}
          </button>
        </div>
      </div>
    </div>
  );
}
