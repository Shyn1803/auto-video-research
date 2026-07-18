/**
 * VersionRestoreDialog tests — task 5-9 Step 4/5 AC (BR-1, BR-2, AC-2, AC-3, AC-5).
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VersionRestoreDialog from "../VersionRestoreDialog";

const { restoreVersionMock } = vi.hoisted(() => ({
  restoreVersionMock: vi.fn(),
}));

vi.mock("@/lib/api/versions", () => ({
  restoreVersion: restoreVersionMock,
}));

const VERSION = {
  id: "v2",
  version: 2,
  step: "scene_set",
  stale: false,
  parent_version: 1,
  created_by: "user1",
  created_at: "2026-07-17T10:00:00Z",
};

describe("VersionRestoreDialog", () => {
  beforeEach(() => {
    restoreVersionMock.mockReset();
  });

  it("restore-uses-1-5-response-staled_steps: BR-1 single path, AC-2 downstream stations flip via response.staled_steps", async () => {
    restoreVersionMock.mockResolvedValue({
      restored: VERSION,
      staled_steps: ["produce", "render"],
    });
    const onRestored = vi.fn();

    render(
      <VersionRestoreDialog
        projectId="p1"
        step="scene_set"
        version={VERSION}
        projectStatus="idle"
        onClose={vi.fn()}
        onRestored={onRestored}
      />,
    );

    // AC-2: confirm states the consequence before confirming.
    expect(screen.getByText(/Hoàn thiện sẽ lỗi thời/)).toBeInTheDocument();
    expect(screen.getByText("Hoàn thiện")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Khôi phục" }));

    await waitFor(() => expect(restoreVersionMock).toHaveBeenCalledWith("p1", "scene_set", 2));
    await waitFor(() => expect(onRestored).toHaveBeenCalledWith(["produce", "render"]));
  });

  it("in-flight-autosave-defers-switch-no-data-loss (BR-2/AC-3): restore call is held until saveStatus leaves 'saving'", async () => {
    restoreVersionMock.mockResolvedValue({ restored: VERSION, staled_steps: [] });
    const onRestored = vi.fn();

    const { rerender } = render(
      <VersionRestoreDialog
        projectId="p1"
        step="scene_set"
        version={VERSION}
        projectStatus="idle"
        saveStatus="saving"
        onClose={vi.fn()}
        onRestored={onRestored}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Khôi phục|Chờ lưu/ }));

    // Deferred: no restore call yet, edit not discarded.
    expect(restoreVersionMock).not.toHaveBeenCalled();
    expect(screen.getByText(/Đang chờ lưu xong/)).toBeInTheDocument();

    // Autosave completes.
    rerender(
      <VersionRestoreDialog
        projectId="p1"
        step="scene_set"
        version={VERSION}
        projectStatus="idle"
        saveStatus="saved"
        onClose={vi.fn()}
        onRestored={onRestored}
      />,
    );

    await waitFor(() => expect(restoreVersionMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onRestored).toHaveBeenCalled());
  });

  it("RUNNING-disables-restore-with-tooltip (AC-5): restore disabled + explanatory tooltip while project is running", () => {
    render(
      <VersionRestoreDialog
        projectId="p1"
        step="scene_set"
        version={VERSION}
        projectStatus="running"
        onClose={vi.fn()}
        onRestored={vi.fn()}
      />,
    );

    const btn = screen.getByRole("button", { name: "Khôi phục" });
    expect(btn).toHaveAttribute("aria-disabled", "true");
    expect(btn).toHaveAttribute("title", expect.stringMatching(/đang chạy/i));

    fireEvent.click(btn);
    expect(restoreVersionMock).not.toHaveBeenCalled();
  });

  it("surfaces a 409 error distinctly when the project starts running mid-flow", async () => {
    restoreVersionMock.mockRejectedValue({ response: { status: 409 } });

    render(
      <VersionRestoreDialog
        projectId="p1"
        step="scene_set"
        version={VERSION}
        projectStatus="idle"
        onClose={vi.fn()}
        onRestored={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Khôi phục" }));
    await waitFor(() =>
      expect(screen.getByText(/Không thể khôi phục khi dự án đang chạy/)).toBeInTheDocument(),
    );
  });
});
