/**
 * RunningState tests — Task 5-8 Step 1 (BR-1, AC-5).
 *
 * Test-directory note: `docs/dev-guide.md` §1 doesn't define a frontend
 * unit-test convention (see memory/project-memory.md Open Questions), and
 * the task file's stated path (`frontend/tests/unit/components/...`) isn't
 * picked up by the actual `vitest.config.ts` (`include:
 * ["src/**\/*.test.{ts,tsx}"]`). Following the convention already used by
 * every sibling workspace component (PipelineStepper, StaleConfirmDialog):
 * co-located `__tests__/*.test.tsx` under `src/components/workspace/`.
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RunningState, { formatElapsed } from "../RunningState";

describe("formatElapsed", () => {
  it("formats seconds under a minute as mm:ss", () => {
    expect(formatElapsed(5_000)).toBe("00:05");
  });

  it("formats minutes correctly", () => {
    expect(formatElapsed(65_000)).toBe("01:05");
  });

  it("formats past an hour as h:mm:ss", () => {
    expect(formatElapsed(3_661_000)).toBe("1:01:01");
  });
});

describe("RunningState", () => {
  it("renders the latest real SSE message verbatim (BR-1)", () => {
    render(
      <RunningState
        stepKind="scenes"
        stepLabel="Phân cảnh"
        message="Đang tạo phân cảnh…"
        startedAt={Date.now()}
      />,
    );
    expect(screen.getByText("Đang tạo phân cảnh…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Đang chạy: Phân cảnh");
  });

  it("shows an indeterminate progress affordance when pct is null (no fabricated %)", () => {
    render(
      <RunningState
        stepKind="research"
        message="Đang đọc nguồn X (4/12)"
        pct={null}
        startedAt={Date.now()}
      />,
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).not.toHaveAttribute("aria-valuenow");
    expect(bar).toHaveAttribute("aria-label", "Đang xử lý, chưa có tiến độ cụ thể");
  });

  it("shows a determinate bar only when a real pct (0 < pct <= 100) is provided", () => {
    render(
      <RunningState stepKind="research" message="Đang xử lý" pct={42} startedAt={Date.now()} />,
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "42");
  });

  it("treats pct=0 as indeterminate (matches today's backend 'started' placeholder, not a real fraction)", () => {
    render(<RunningState stepKind="research" message="Đang xử lý" pct={0} startedAt={Date.now()} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).not.toHaveAttribute("aria-valuenow");
  });

  it("falls back to a generic message when none has arrived yet", () => {
    render(<RunningState stepKind="research" message={null} startedAt={Date.now()} />);
    expect(screen.getByText("Đang xử lý…")).toBeInTheDocument();
  });

  it("applies motion-safe (not unconditional animate-pulse) to the indeterminate sweep for reduced-motion users (AC-5)", () => {
    const { container } = render(
      <RunningState stepKind="research" message="Đang xử lý" pct={null} startedAt={Date.now()} />,
    );
    const sweep = container.querySelector(".motion-safe\\:animate-pulse");
    expect(sweep).not.toBeNull();
    expect(sweep?.className).not.toMatch(/(?<!motion-safe:)animate-pulse/);
  });

  it("renders Chạy ngầm only while running, and calls onBackground on click", () => {
    const onBackground = vi.fn();
    render(
      <RunningState
        stepKind="research"
        message="Đang xử lý"
        startedAt={Date.now()}
        onBackground={onBackground}
        status="running"
      />,
    );
    screen.getByText("Chạy ngầm").click();
    expect(onBackground).toHaveBeenCalledOnce();
  });

  it("shows 'Đang huỷ…' and disables the button in cancelling status", () => {
    render(
      <RunningState
        stepKind="research"
        message="Đang xử lý"
        startedAt={Date.now()}
        onCancel={() => {}}
        status="cancelling"
      />,
    );
    const btn = screen.getByText("Đang huỷ…");
    expect(btn).toBeDisabled();
  });
});
