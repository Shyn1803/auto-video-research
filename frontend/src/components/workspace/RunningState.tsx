/**
 * RunningState — universal "đang chạy" UI for every AI pipeline step.
 *
 * Design-system §3.4 / task 5-8: this is the single component every
 * Duyệt→AI-step transition renders (research, content, scenes, ...). It is
 * intentionally decoupled from any one screen — callers feed it real SSE
 * data (via `useEventStream`, task 1-6) rather than it opening its own
 * connection, so it stays reusable across 5-6/5-7/5-9 integration points.
 *
 * BR-1 (core anti-pattern this exists to prevent): never invent a
 * percentage. `pct` is `number | null` — the caller passes `null` whenever
 * the latest `step.progress` event's payload has no meaningful fractional
 * value (today's backend, see `app/services/run_service.py` /
 * `app/pipeline/nodes/research/node.py`, publishes `pct=0` as a "started"
 * placeholder and `pct=100` as "completed", not a real fraction in
 * between yet) — the component renders an indeterminate spinner/bar in
 * that case and never fabricates a number to fill the gap.
 */

"use client";

import { useEffect, useState } from "react";

export type RunningStateStatus = "running" | "cancelling" | "error" | "done";

export interface RunningStateProps {
  /** Station/step key, e.g. "research" | "content" | "scenes" | "finish" | "publish". */
  stepKind: string;
  /** Human label for the step; falls back to `stepKind` if not given. */
  stepLabel?: string;
  /** Latest real SSE message, rendered verbatim — never paraphrased or padded (BR-1). */
  message: string | null;
  /**
   * Real fractional progress, 0-100, or `null` when the latest event carries
   * no meaningful percentage. `null` (or omitted) renders an indeterminate
   * progress affordance instead of a fabricated bar.
   */
  pct?: number | null;
  /** Epoch ms the run started — used to compute the elapsed-time readout. */
  startedAt: number;
  status?: RunningStateStatus;
  /** "Chạy ngầm" — background the run (wired in Step 2). */
  onBackground?: () => void;
  /** "Huỷ" — cancel the run (wired in Step 4, RunningStateCancel). */
  onCancel?: () => void;
  className?: string;
}

/** mm:ss (or h:mm:ss past an hour) elapsed-time formatter. */
export function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** Live-updating elapsed-time readout, ticking once per second. */
function useElapsed(startedAt: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return now - startedAt;
}

export default function RunningState({
  stepKind,
  stepLabel,
  message,
  pct = null,
  startedAt,
  status = "running",
  onBackground,
  onCancel,
  className,
}: RunningStateProps) {
  const elapsedMs = useElapsed(startedAt);
  const label = stepLabel ?? stepKind;
  const isDeterminate = typeof pct === "number" && pct > 0 && pct <= 100;

  return (
    <div
      role="status"
      aria-label={`Đang chạy: ${label}`}
      data-step-kind={stepKind}
      data-status={status}
      className={`flex flex-col gap-4 rounded-xl border border-border bg-card p-6 ${className ?? ""}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{label}</h3>
        <span className="text-xs tabular-nums text-muted-foreground" aria-label="Thời gian đã chạy">
          {formatElapsed(elapsedMs)}
        </span>
      </div>

      {/* BR-1: message + progress region — the only part screen readers need
          re-announced on update, so aria-live is scoped here, not on the
          whole card (which would also re-announce the elapsed-time ticks). */}
      <div aria-live="polite" aria-atomic="true" className="flex flex-col gap-2">
        <p className="text-sm text-foreground">
          {message ?? "Đang xử lý…"}
        </p>

        {isDeterminate ? (
          <div
            role="progressbar"
            aria-valuenow={pct as number}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        ) : (
          <div
            role="progressbar"
            aria-label="Đang xử lý, chưa có tiến độ cụ thể"
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
          >
            {/* motion-safe: — reduced-motion users get a static bar (AC-5),
                everyone else gets a moving indeterminate sweep. */}
            <div className="h-full w-1/3 motion-safe:animate-pulse rounded-full bg-primary/60" />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 pt-1">
        {onBackground && status === "running" && (
          <button
            type="button"
            onClick={onBackground}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Chạy ngầm
          </button>
        )}
        {onCancel && (status === "running" || status === "cancelling") && (
          <button
            type="button"
            onClick={onCancel}
            disabled={status === "cancelling"}
            className="rounded-lg border border-status-fail/40 px-3 py-1.5 text-xs font-medium text-status-fail hover:bg-status-fail/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {status === "cancelling" ? "Đang huỷ…" : "Huỷ"}
          </button>
        )}
      </div>
    </div>
  );
}
