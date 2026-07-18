/**
 * RunningStateOverlay — the single drop-in integration point for "every
 * Duyệt→AI-step transition" (task 5-8 Step 5).
 *
 * Why this exists rather than wiring RunningState/RunningStateError/
 * RunningStateCancel + `useEventStream` separately into each station page:
 * as of this task, only `scenes/page.tsx` exists among the 5 station
 * pages, and its "Duyệt" action is local station navigation (no AI-step
 * API call yet — see its own comments, `5-2`/`5-5` wire the real calls).
 * Tasks 5-6 (Nghiên cứu) and 5-7 (Nội dung) are the ones that will
 * actually trigger `POST /projects/{id}/steps/{step}/run` and need this
 * mounted — this component is their integration surface, built generic
 * (`stepKind`, no screen-specific logic) so they can drop it in without
 * rework, per this task file's own note.
 *
 * Combines: `useEventStream` (1-6) for real SSE progress/cancellation,
 * `RunningState` (message/elapsed/indeterminate + Chạy ngầm), auto-`onDone`
 * transition (AC-1), `RunningStateError` (BR-2) once the run's status
 * indicates failure, and `RunningStateCancel` (BR-3/BR-4, consumes 4-7).
 */

"use client";

import { useEffect, useRef, useState } from "react";
import RunningState from "./RunningState";
import RunningStateError, { type RunningStateErrorData, type ViewerRole } from "./RunningStateError";
import RunningStateCancel from "./RunningStateCancel";
import { useEventStream, type UseEventStreamOptions, type RunProgress } from "@/hooks/useEventStream";

export interface RunningStateOverlayProps {
  projectId: string;
  runId: string;
  stepKind: string;
  stepLabel?: string;
  /** Epoch ms the run started. */
  startedAt: number;
  viewerRole: ViewerRole;
  /** Fires once when the run reaches a terminal "done" status (AC-1 auto-transition). */
  onDone?: () => void;
  /** Shape the current run snapshot into a classified error once status looks failed. */
  classifyError?: (run: RunProgress) => RunningStateErrorData | null;
  onRetry?: () => void;
  onResume?: () => void;
  /** Called when the user clicks "Chạy ngầm" — the caller decides what to render instead
   *  (typically nothing here + a ProjectProgressCard on the dashboard). */
  onBackground?: () => void;
  className?: string;
  /** Test seam / advanced override. */
  useEventStreamHook?: (opts: UseEventStreamOptions) => RunProgress;
}

const DONE_STATUSES = new Set(["done", "completed", "ready", "published"]);
const FAILED_STATUSES = new Set(["failed", "error"]);

export default function RunningStateOverlay({
  projectId,
  runId,
  stepKind,
  stepLabel,
  startedAt,
  viewerRole,
  onDone,
  classifyError,
  onRetry,
  onResume,
  onBackground,
  className,
  useEventStreamHook = useEventStream,
}: RunningStateOverlayProps) {
  const [backgrounded, setBackgrounded] = useState(false);
  const [cancelConfirmed, setCancelConfirmed] = useState(false);
  const doneFiredRef = useRef(false);

  const progress = useEventStreamHook({
    projectId,
    runId,
    onEvent: (ev) => {
      if (ev.event_type === "run.cancelled") setCancelConfirmed(true);
    },
  });

  useEffect(() => {
    if (progress.status && DONE_STATUSES.has(progress.status) && !doneFiredRef.current) {
      doneFiredRef.current = true;
      onDone?.();
    }
  }, [progress.status, onDone]);

  if (backgrounded) {
    // Caller owns what renders in this station's place while backgrounded
    // (typically nothing — the dashboard's ProjectProgressCard + the
    // stepper's background badge are the visible affordances at that point).
    return null;
  }

  const isFailed = Boolean(progress.status && FAILED_STATUSES.has(progress.status));
  const error = isFailed ? classifyError?.(progress) ?? null : null;

  if (error) {
    return (
      <RunningStateError error={error} viewerRole={viewerRole} onRetry={onRetry} className={className} />
    );
  }

  const message = (progress.lastEvent?.payload as { message?: string } | undefined)?.message ?? null;
  // BR-1 parity with RunningState/ProjectProgressCard: only a genuine
  // in-between fraction counts as "real" -- today's backend's 0/100
  // sentinel values fall back to indeterminate.
  const pct = progress.progressPct > 0 && progress.progressPct < 100 ? progress.progressPct : null;

  return (
    <div className={`flex flex-col gap-3 ${className ?? ""}`}>
      <RunningState
        stepKind={stepKind}
        stepLabel={stepLabel}
        message={message}
        pct={pct}
        startedAt={startedAt}
        status={cancelConfirmed ? "done" : "running"}
        onBackground={() => {
          setBackgrounded(true);
          onBackground?.();
        }}
      />
      <RunningStateCancel
        projectId={projectId}
        runId={runId}
        startedAt={startedAt}
        cancelConfirmed={cancelConfirmed}
        onResume={onResume}
      />
    </div>
  );
}
