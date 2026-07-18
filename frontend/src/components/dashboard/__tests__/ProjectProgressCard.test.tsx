/**
 * ProjectProgressCard tests — Task 5-8 Step 2 (AC-2).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectProgressCard } from "../ProjectProgressCard";
import type { RunProgress } from "@/hooks/useEventStream";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function fakeStream(overrides: Partial<RunProgress>): () => RunProgress {
  return () => ({
    runId: "run-1",
    status: "running",
    currentStep: "research",
    progressPct: 0,
    lastEvent: null,
    connected: true,
    ...overrides,
  });
}

describe("ProjectProgressCard", () => {
  it("shows an indeterminate ● when no real fraction is present (BR-1 parity)", () => {
    render(
      <ProjectProgressCard
        projectId="p1"
        projectName="Dự án A"
        runId="run-1"
        useEventStreamHook={fakeStream({ progressPct: 0 })}
      />,
    );
    expect(screen.getByText(/đang xử lý/)).toBeInTheDocument();
  });

  it("shows a determinate percentage when the stream reports a real in-between pct", () => {
    render(
      <ProjectProgressCard
        projectId="p1"
        projectName="Dự án A"
        runId="run-1"
        useEventStreamHook={fakeStream({ progressPct: 42, currentStep: "scenes" })}
      />,
    );
    expect(screen.getByTestId("progress-caption").textContent).toContain("42%");
  });

  it("click-through calls onOpen with the project id (dashboard → workspace at current progress)", () => {
    const onOpen = vi.fn();
    render(
      <ProjectProgressCard
        projectId="p1"
        projectName="Dự án A"
        runId="run-1"
        onOpen={onOpen}
        useEventStreamHook={fakeStream({})}
      />,
    );
    screen.getByRole("link").click();
    expect(onOpen).toHaveBeenCalledWith("p1");
  });

  it("surfaces the latest real SSE message alongside the step label", () => {
    render(
      <ProjectProgressCard
        projectId="p1"
        projectName="Dự án A"
        runId="run-1"
        useEventStreamHook={fakeStream({
          currentStep: "research",
          lastEvent: {
            event_id: "e1",
            event_type: "step.progress",
            schema_version: "1.0.0",
            occurred_at: "2026-07-18T00:00:00Z",
            correlation_id: "run-1",
            payload: { message: "Đang đọc nguồn X (4/12)" },
          },
        })}
      />,
    );
    expect(screen.getByTestId("progress-caption").textContent).toContain(
      "Đang đọc nguồn X (4/12)",
    );
  });
});
