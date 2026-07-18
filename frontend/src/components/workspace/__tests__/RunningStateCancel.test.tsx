/**
 * RunningStateCancel tests — Task 5-8 Step 4 (BR-3, BR-4).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RunningStateCancel from "../RunningStateCancel";

describe("RunningStateCancel", () => {
  it("under 30s: cancels immediately, no confirm dialog (BR-3)", async () => {
    const cancelApi = vi.fn().mockResolvedValue({ cancelling: true });
    const now = () => 1_000 + 10_000; // 10s elapsed
    render(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={false}
        now={now}
        cancelApi={cancelApi}
      />,
    );
    fireEvent.click(screen.getByText("Huỷ"));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(cancelApi).toHaveBeenCalledWith("p1", "r1");
  });

  it("over 30s: requires confirm before cancelling (BR-3)", () => {
    const cancelApi = vi.fn().mockResolvedValue({ cancelling: true });
    const now = () => 1_000 + 45_000; // 45s elapsed
    render(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={false}
        now={now}
        cancelApi={cancelApi}
      />,
    );
    fireEvent.click(screen.getByText("Huỷ"));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByText(/kết quả các bước đã xong vẫn được giữ lại/)).toBeInTheDocument();
    expect(cancelApi).not.toHaveBeenCalled();

    // Confirming actually calls the API.
    fireEvent.click(screen.getByRole("button", { name: "Huỷ" }));
    expect(cancelApi).toHaveBeenCalledWith("p1", "r1");
  });

  it("dismissing the confirm dialog does not cancel", () => {
    const cancelApi = vi.fn().mockResolvedValue({ cancelling: true });
    const now = () => 1_000 + 45_000;
    render(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={false}
        now={now}
        cancelApi={cancelApi}
      />,
    );
    fireEvent.click(screen.getByText("Huỷ"));
    fireEvent.click(screen.getByText("Không huỷ"));
    expect(cancelApi).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("shows 'Đang huỷ…' after requesting, until the real event confirms it (BR-4)", async () => {
    let resolveCancel: (v: { cancelling: boolean }) => void = () => {};
    const cancelApi = vi.fn(
      () =>
        new Promise<{ cancelling: boolean }>((resolve) => {
          resolveCancel = resolve;
        }),
    );
    const now = () => 1_000 + 5_000;
    const { rerender } = render(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={false}
        now={now}
        cancelApi={cancelApi}
      />,
    );
    fireEvent.click(screen.getByText("Huỷ"));
    expect(await screen.findByText("Đang huỷ…")).toBeInTheDocument();

    resolveCancel({ cancelling: true });
    // Even after the POST resolves, we must NOT optimistically show
    // "cancelled" -- only the real event (cancelConfirmed=true) does that.
    await Promise.resolve();
    expect(screen.getByText("Đang huỷ…")).toBeInTheDocument();
    expect(screen.queryByText("Đã huỷ.")).toBeNull();

    // Now the parent observed the real run.cancelled SSE event.
    rerender(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={true}
        now={now}
        cancelApi={cancelApi}
      />,
    );
    expect(screen.getByText("Đã huỷ.")).toBeInTheDocument();
  });

  it("offers 'Chạy tiếp?' once cancelled, wired to onResume", () => {
    const onResume = vi.fn();
    render(
      <RunningStateCancel
        projectId="p1"
        runId="r1"
        startedAt={1_000}
        cancelConfirmed={true}
        onResume={onResume}
        cancelApi={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Chạy tiếp?"));
    expect(onResume).toHaveBeenCalledOnce();
  });
});
