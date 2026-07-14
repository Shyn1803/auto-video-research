"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { openSse, type SseMessageHandler } from "@/lib/sse";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Pipeline run event received over SSE.
 *
 * Matches the two canonical event types emitted by the backend:
 * - ``project.status``  payload: { project_id, from_state, to_state, actor?, reason? }
 * - ``step.progress``   payload: { project_id, run_id, step, pct, message? }
 */
export interface PipelineEvent {
  event_id: string;
  event_type: "project.status" | "step.progress";
  schema_version: string;
  occurred_at: string;
  correlation_id: string;
  payload: Record<string, unknown>;
}

/** Aggregated run progress derived from SSE events. */
export interface RunProgress {
  runId: string | null;
  status: string | null;
  currentStep: string | null;
  progressPct: number;
  lastEvent: PipelineEvent | null;
  connected: boolean;
}

/** Options accepted by the hook. */
export interface UseEventStreamOptions {
  projectId: string;
  runId: string;
  /** Called on every parsed event — use to update your own state. */
  onEvent?: (ev: PipelineEvent) => void;
}

/** Back-off schedule for SSE reconnect (ms). */
const RECONNECT_DELAYS = [500, 1_500, 3_000, 5_000, 10_000];

export function useEventStream({ projectId, runId, onEvent }: UseEventStreamOptions): RunProgress {
  const [status, setStatus] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [progressPct, setProgressPct] = useState(0);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<PipelineEvent | null>(null);

  // Track reconnect attempt across multiple SSE sessions within one hook lifetime.
  const attemptIdx = useRef(0);
  const teardownRef = useRef<(() => void) | null>(null);
  const isMounted = useRef(true);

  // Keep refs current so the reconnect callback always has latest values.
  const projectIdRef = useRef(projectId);
  const runIdRef = useRef(runId);
  const onEventRef = useRef(onEvent);
  projectIdRef.current = projectId;
  runIdRef.current = runId;
  onEventRef.current = onEvent;

  // ---------------------------------------------------------------------------
  // Fetch a fresh one-time token (BR-3: 60 s TTL, single use)
  // ---------------------------------------------------------------------------
  const fetchToken = useCallback(async (): Promise<string> => {
    const tokenRes = await fetch(
      `${API_BASE}/events/token?project_id=${encodeURIComponent(projectId)}`,
      { method: "POST", credentials: "include" },
    );
    if (!tokenRes.ok) {
      const detail = await tokenRes.text();
      throw new Error(`token 401 – ${detail}`);
    }
    const { token } = (await tokenRes.json()) as { token: string };
    return token;
  }, [projectId]);

  // ---------------------------------------------------------------------------
  // Poll fallback — called once after reconnect to fill missed events (BR-4)
  // ---------------------------------------------------------------------------
  const pollSnapshot = useCallback(
    async (candidateRunId: string) => {
      try {
        const res = await fetch(`${API_BASE}/runs/${candidateRunId}`, {
          credentials: "include",
        });
        if (!res.ok) return;
        const run = (await res.json()) as {
          status?: string;
          current_step?: string | null;
          progress_pct?: number;
        };
        if (isMounted.current) {
          if (run.status) setStatus(run.status);
          setCurrentStep(run.current_step ?? null);
          setProgressPct(run.progress_pct ?? 0);
        }
      } catch {
        // Poll failed — non-blocking; the SSE stream will resync when it emits.
      }
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Inner connect logic — open SSE, register event handler, attach error handler
  // ---------------------------------------------------------------------------
  const connect = useCallback(
    async (attempt: number) => {
      let token: string;
      try {
        token = await fetchToken();
      } catch {
        // Can't get a token — try again with back-off.
        if (isMounted.current) {
          const delay = RECONNECT_DELAYS[Math.min(attempt, RECONNECT_DELAYS.length - 1)];
          setTimeout(() => connect(attempt + 1), delay);
        }
        return;
      }

      const streamUrl = `${API_BASE}/events/stream?token=${token}`;
      // Derive a fresh runId — in case it changed between connects.
      const effectiveRunId = runIdRef.current;

      const onMessage: SseMessageHandler = (data) => {
        const ev = data as PipelineEvent;
        if (isMounted.current) {
          setLastEvent(ev);
          onEventRef.current?.(ev);

          // Update local state from event payload
          if (ev.event_type === "project.status") {
            const p = ev.payload as {
              to_state?: string;
              from_state?: string;
              actor?: string;
            };
            if (p.to_state) setStatus(p.to_state);
          }
          if (ev.event_type === "step.progress") {
            const p = ev.payload as { step?: string; pct?: number };
            if (p.step) setCurrentStep(p.step);
            if (typeof p.pct === "number") setProgressPct(p.pct);
          }
        }
      };

      const onError = () => {
        if (isMounted.current) setConnected(false);
        // BR-4: after reconnect, poll for snapshot so we resync missed state.
        pollSnapshot(effectiveRunId);
        const delay = RECONNECT_DELAYS[Math.min(attempt, RECONNECT_DELAYS.length - 1)];
        setTimeout(() => connect(attempt + 1), delay);
      };

      const teardown = openSse(streamUrl, {
        onMessage,
        onError,
        onClose: () => {
          if (isMounted.current) setConnected(false);
        },
      });

      teardownRef.current = teardown;
      if (isMounted.current) setConnected(true);
    },
    [fetchToken, pollSnapshot],
  );

  // ---------------------------------------------------------------------------
  // Lifecycle: connect on mount / projectId+runId change; teardown on unmount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    isMounted.current = true;
    attemptIdx.current = 0;
    // BR-4: resync on connect — poll once before opening the stream.
    pollSnapshot(runIdRef.current).finally(() => {
      connect(0);
    });

    return () => {
      isMounted.current = false;
      teardownRef.current?.();
    };
  }, [projectId, runId, connect, pollSnapshot]);

  return {
    runId,
    status,
    currentStep,
    progressPct,
    lastEvent,
    connected,
  };
}
