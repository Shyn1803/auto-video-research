/**
 * RunningStateOverlay tests — Task 5-8 Step 5 (AC-1 auto-transition,
 * generic reusable integration point for 5-6/5-7).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RunningStateOverlay from "../RunningStateOverlay";
import type { RunProgress, UseEventStreamOptions } from "@/hooks/useEventStream";

function fakeStreamHook(progress: RunProgress) {
  return (_opts: UseEventStreamOptions) => progress;
}

describe("RunningStateOverlay", () => {
  it("renders RunningState with the real message + step while running", () => {
    render(
      <RunningStateOverlay
        projectId="p1"
        runId="r1"
        stepKind="scenes"
        stepLabel="Phân cảnh"
        startedAt={Date.now()}
        viewerRole="creator"
        useEventStreamHook={fakeStreamHook({
          runId: "r1",
          status: "running",
          currentStep: "scenes",
          progressPct: 0,
          lastEvent: {
            event_id: "e1",
            event_type: "step.progress",
            schema_version: "1.0.0",
            occurred_at: "2026-07-18T00:00:00Z",
            correlation_id: "r1",
            payload: { message: "Đang tạo phân cảnh…" },
          },
          connected: true,
        })}
      />,
    );
    expect(screen.getByText("Đang tạo phân cảnh…")).toBeInTheDocument();
  });

  it("AC-1: fires onDone exactly once when the run reaches a done status", () => {
    const onDone = vi.fn();
    render(
      <RunningStateOverlay
        projectId="p1"
        runId="r1"
        stepKind="scenes"
        startedAt={Date.now()}
        viewerRole="creator"
        onDone={onDone}
        useEventStreamHook={fakeStreamHook({
          runId: "r1",
          status: "done",
          currentStep: "scenes",
          progressPct: 100,
          lastEvent: null,
          connected: true,
        })}
      />,
    );
    expect(onDone).toHaveBeenCalledOnce();
  });

  it("BR-2: renders RunningStateError once classifyError returns a variant for a failed run", () => {
    render(
      <RunningStateOverlay
        projectId="p1"
        runId="r1"
        stepKind="research"
        startedAt={Date.now()}
        viewerRole="admin"
        classifyError={() => ({
          kind: "all_providers_failed",
          capability: "llm_cheap",
          chain: ["ollama"],
          failures: [{ provider: "ollama", reason: "unreachable" }],
        })}
        useEventStreamHook={fakeStreamHook({
          runId: "r1",
          status: "failed",
          currentStep: "research",
          progressPct: 0,
          lastEvent: null,
          connected: true,
        })}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/ollama/)).toBeInTheDocument();
  });

  it("hides the overlay once backgrounded via 'Chạy ngầm' and calls onBackground", () => {
    const onBackground = vi.fn();
    render(
      <RunningStateOverlay
        projectId="p1"
        runId="r1"
        stepKind="research"
        startedAt={Date.now()}
        viewerRole="creator"
        onBackground={onBackground}
        useEventStreamHook={fakeStreamHook({
          runId: "r1",
          status: "running",
          currentStep: "research",
          progressPct: 0,
          lastEvent: null,
          connected: true,
        })}
      />,
    );
    fireEvent.click(screen.getByText("Chạy ngầm"));
    expect(onBackground).toHaveBeenCalledOnce();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
