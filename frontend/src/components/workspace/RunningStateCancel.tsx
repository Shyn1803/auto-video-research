/**
 * RunningStateCancel — Huỷ flow for a running AI step (BR-3, BR-4).
 *
 * Consumes task 4-7's backend: `POST /projects/{id}/runs/{run_id}/cancel`
 * (best-effort, finishes after the current node genuinely stops — see
 * `docs/specs/api-spec.md`) and the `run.cancelled` event it eventually
 * publishes (`{project_id, run_id, step}`, `docs/specs/event-catalog.md`).
 *
 * BR-3: if the run has been active >30s, confirm first — warn that
 * already-finished sub-steps' results are kept.
 * BR-4 (matches 4-7's own BR-1): after confirming, show "Đang huỷ…" and
 * stay there until the real `run.cancelled` event arrives — this component
 * never optimistically flips to "cancelled" on the strength of the POST
 * response alone (the POST's `cancelling: true` only means the request was
 * accepted, not that the node has actually stopped). The caller owns the
 * SSE subscription (via `useEventStream`, task 1-6) and passes
 * `cancelConfirmed` once it sees that event — this component stays a pure
 * function of that prop rather than opening a second stream connection.
 *
 * "Chạy tiếp" after a confirmed cancel re-runs `POST
 * /projects/{id}/steps/{step}/run` (resumes the same run's checkpoint,
 * doesn't start a new thread) per api-spec.md's note on the cancel route —
 * this component only surfaces the button; the caller supplies `onResume`.
 */

"use client";

import { useState } from "react";
import { api } from "@/lib/api/interceptor";

export type CancelPhase = "idle" | "confirming" | "cancelling" | "cancelled";

const CONFIRM_THRESHOLD_MS = 30_000;

export interface RunningStateCancelProps {
  projectId: string;
  runId: string;
  /** Epoch ms the run started — drives the BR-3 >30s confirm threshold. */
  startedAt: number;
  /** Set true once the caller's SSE listener has observed `run.cancelled`. */
  cancelConfirmed: boolean;
  onCancelRequested?: () => void;
  onResume?: () => void;
  className?: string;
  /** Test seams. */
  now?: () => number;
  cancelApi?: (projectId: string, runId: string) => Promise<{ cancelling: boolean }>;
}

async function defaultCancelApi(
  projectId: string,
  runId: string,
): Promise<{ cancelling: boolean }> {
  const { data } = await api.post<{ run_id: string; status: string; cancelling: boolean }>(
    `/projects/${projectId}/runs/${runId}/cancel`,
  );
  return { cancelling: data.cancelling };
}

export default function RunningStateCancel({
  projectId,
  runId,
  startedAt,
  cancelConfirmed,
  onCancelRequested,
  onResume,
  className,
  now = Date.now,
  cancelApi = defaultCancelApi,
}: RunningStateCancelProps) {
  const [phase, setPhase] = useState<CancelPhase>("idle");

  // BR-4: the event, not local state, is the source of truth for "actually
  // cancelled" -- once the parent tells us the event arrived, show the
  // cancelled sub-state regardless of what phase we were mid-way through.
  const effectivePhase: CancelPhase = cancelConfirmed ? "cancelled" : phase;

  const requestCancel = async () => {
    setPhase("cancelling");
    onCancelRequested?.();
    await cancelApi(projectId, runId);
    // Deliberately do not set phase to "cancelled" here (BR-4) -- we wait
    // for `cancelConfirmed` to flip via the real event.
  };

  const handleCancelClick = () => {
    const elapsed = now() - startedAt;
    if (elapsed > CONFIRM_THRESHOLD_MS) {
      setPhase("confirming");
    } else {
      void requestCancel();
    }
  };

  if (effectivePhase === "cancelled") {
    return (
      <div className={`flex items-center gap-3 ${className ?? ""}`}>
        <span className="text-sm text-muted-foreground">Đã huỷ.</span>
        {onResume && (
          <button
            type="button"
            onClick={onResume}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Chạy tiếp?
          </button>
        )}
      </div>
    );
  }

  if (effectivePhase === "confirming") {
    return (
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label="Xác nhận huỷ"
        className={`flex flex-col gap-3 rounded-lg border border-status-fail/40 bg-status-fail/5 p-4 text-sm ${className ?? ""}`}
      >
        <p>Huỷ sẽ dừng bước hiện tại — kết quả các bước đã xong vẫn được giữ lại.</p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setPhase("idle")}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Không huỷ
          </button>
          <button
            type="button"
            onClick={() => void requestCancel()}
            className="rounded-lg bg-status-fail px-3 py-1.5 text-xs font-semibold text-white hover:brightness-110"
          >
            Huỷ
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={handleCancelClick}
      disabled={effectivePhase === "cancelling"}
      className={`rounded-lg border border-status-fail/40 px-3 py-1.5 text-xs font-medium text-status-fail hover:bg-status-fail/10 disabled:cursor-not-allowed disabled:opacity-60 ${className ?? ""}`}
    >
      {effectivePhase === "cancelling" ? "Đang huỷ…" : "Huỷ"}
    </button>
  );
}
