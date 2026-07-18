/**
 * VersionSwitcher — task 5-9 topbar `v3 ▾` dropdown.
 *
 * Lists every version of the current station's versioning step (timestamp,
 * author, stale badge+tooltip — BR-3), with per-row Xem/So sánh/Khôi phục
 * actions. Extends 5-1's Topbar (replaces its `VersionSwitcherCurrent` stub).
 *
 * AC-4 (empty): a step with only 1 version shows an explanatory message
 * instead of an empty/broken dropdown.
 * AC-1: closing Xem/So sánh returns focus to wherever it was opened from —
 * this component owns that (it's the opener), via `returnFocusRef`.
 * BR-2: an in-flight autosave defers the version switch until the save
 * completes rather than discarding the edit — this only applies to
 * switching the *current* editable version (i.e. re-pointing which version
 * is being edited), not to Xem/So sánh which never touch editable state;
 * Khôi phục's own confirm-then-restore flow is inherently a deliberate,
 * explicit action rather than an incidental switch, but we still block it
 * while a save is in flight for the same reason (never discard unsaved text).
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWorkspace, stationIndexForVersioningStep } from "@/lib/workspace-context";
import {
  listVersions,
  getCurrentVersion,
  type VersionOut,
} from "@/lib/api/versions";
import VersionViewOverlay from "./VersionViewOverlay";
import VersionCompare from "./VersionCompare";
import VersionRestoreDialog from "./VersionRestoreDialog";

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function staleTooltip(v: VersionOut): string {
  return `Phiên bản v${v.version} đã lỗi thời — một bước trước đó đã được khôi phục nên nội dung này cần được tạo lại (BR-3).`;
}

export interface VersionSwitcherProps {
  /** override for isolated tests; defaults to workspace-context state */
  step?: string;
}

export default function VersionSwitcher({ step: stepOverride }: VersionSwitcherProps) {
  const { state, dispatch } = useWorkspace();
  const step = stepOverride ?? state.versioningStep;
  const projectId = state.projectId;

  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState<VersionOut[] | null>(null);
  const [currentVersion, setCurrentVersion] = useState<VersionOut | null>(null);
  const [allStale, setAllStale] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [viewingVersion, setViewingVersion] = useState<number | null>(null);
  const [comparingVersion, setComparingVersion] = useState<number | null>(null);
  const [restoringVersion, setRestoringVersion] = useState<VersionOut | null>(null);

  // AC-1: remember whatever was focused before opening an overlay so
  // closing it returns focus to exactly that element.
  const returnFocusRef = useRef<HTMLElement | null>(null);

  const load = useCallback(async () => {
    if (!projectId || !step) return;
    setLoading(true);
    setLoadError(null);
    try {
      const list = await listVersions(projectId, step);
      setVersions(list.versions);
      try {
        const cur = await getCurrentVersion(projectId, step);
        setCurrentVersion(cur.current);
        setAllStale(cur.all_stale);
      } catch {
        setCurrentVersion(null);
        setAllStale(false);
      }
    } catch {
      setLoadError("Không tải được lịch sử phiên bản");
    } finally {
      setLoading(false);
    }
  }, [projectId, step]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  function withReturnFocus(action: () => void) {
    returnFocusRef.current = (document.activeElement as HTMLElement) ?? null;
    action();
  }

  function closeOverlay(after: () => void) {
    after();
    returnFocusRef.current?.focus?.();
  }

  const buttonLabel = currentVersion ? `Phiên bản v${currentVersion.version}` : "Phiên bản";

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent"
      >
        {buttonLabel} ▾
        {allStale && (
          <span
            role="status"
            title="Mọi phiên bản của bước này đều đã lỗi thời"
            className="ml-1 rounded-full bg-status-warn/20 px-1.5 py-0.5 text-[10px] text-status-warn"
          >
            lỗi thời
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Lịch sử phiên bản"
          className="absolute right-0 top-full z-50 mt-2 w-96 rounded-xl border border-border bg-card p-4 shadow-xl"
        >
          {loading && <p className="text-sm text-muted-foreground">Đang tải…</p>}
          {loadError && <p className="text-sm text-status-fail">{loadError}</p>}

          {!loading && !loadError && versions && versions.length <= 1 && (
            <p className="text-sm text-muted-foreground">
              Chỉ có 1 phiên bản — chưa có lịch sử để xem hoặc so sánh.
            </p>
          )}

          {!loading && !loadError && versions && versions.length > 1 && (
            <ul className="divide-y divide-border">
              {versions.map((v) => (
                <li key={v.id} className="flex items-center justify-between gap-2 py-2">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">
                      v{v.version}
                      {currentVersion && v.version === currentVersion.version && (
                        <span className="ml-1 text-xs font-normal text-muted-foreground">
                          (hiện hành)
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatTimestamp(v.created_at)} · {v.created_by}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {v.stale && (
                      <span
                        role="status"
                        title={staleTooltip(v)}
                        className="rounded-full border border-status-warn/40 bg-status-warn/10 px-1.5 py-0.5 text-[10px] text-status-warn"
                      >
                        lỗi thời
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => withReturnFocus(() => setViewingVersion(v.version))}
                      className="text-xs text-muted-foreground underline hover:text-foreground"
                    >
                      Xem
                    </button>
                    <button
                      type="button"
                      onClick={() => withReturnFocus(() => setComparingVersion(v.version))}
                      className="text-xs text-muted-foreground underline hover:text-foreground"
                    >
                      So sánh
                    </button>
                    <button
                      type="button"
                      onClick={() => setRestoringVersion(v)}
                      className="text-xs text-muted-foreground underline hover:text-foreground"
                    >
                      Khôi phục
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {viewingVersion !== null && (
        <VersionViewOverlay
          projectId={projectId}
          step={step}
          version={viewingVersion}
          onClose={() => closeOverlay(() => setViewingVersion(null))}
        />
      )}

      {comparingVersion !== null && currentVersion && (
        <VersionCompare
          projectId={projectId}
          step={step}
          fromVersion={comparingVersion}
          toVersion={currentVersion.version}
          onClose={() => closeOverlay(() => setComparingVersion(null))}
        />
      )}

      {restoringVersion && (
        <VersionRestoreDialog
          projectId={projectId}
          step={step}
          version={restoringVersion}
          projectStatus={state.projectStatus}
          saveStatus={state.saveStatus}
          unsavedChanges={state.unsavedChanges}
          onClose={() => setRestoringVersion(null)}
          onRestored={(staledSteps) => {
            const stationIndexes = staledSteps
              .map((s) => stationIndexForVersioningStep(s))
              .filter((i) => i >= 0);
            dispatch({ type: "MARK_STATIONS_STALE", stationIndexes });
            setRestoringVersion(null);
            load();
          }}
        />
      )}
    </div>
  );
}
