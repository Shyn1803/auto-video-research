/**
 * StaleConfirmDialog tests — Task 5-1 Step 7 (BR-1).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WorkspaceProvider } from "@/lib/workspace-context";
import { StaleConfirmDialog, staleStationLabels } from "../StaleConfirmDialog";

describe("staleStationLabels", () => {
  it("lists only done/done-warning stations after fromIndex", () => {
    const labels = staleStationLabels(
      ["done", "done", "current", "done-warning", "locked"],
      2,
    );
    expect(labels).toEqual(["Hoàn thiện"]);
  });

  it("returns empty when nothing after fromIndex is done", () => {
    const labels = staleStationLabels(["done", "done", "current", "locked", "locked"], 2);
    expect(labels).toEqual([]);
  });
});

describe("StaleConfirmDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <WorkspaceProvider projectId="p1">
        <StaleConfirmDialog open={false} fromIndex={0} onCancel={() => {}} onConfirm={() => {}} />
      </WorkspaceProvider>,
    );
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("lists stale-to-be stations and confirms/cancels", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <WorkspaceProvider
        projectId="p1"
        initialState={{ stationStates: ["done", "current", "done", "locked", "locked"] }}
      >
        <StaleConfirmDialog open fromIndex={1} onCancel={onCancel} onConfirm={onConfirm} />
      </WorkspaceProvider>,
    );
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("Phân cảnh");

    fireEvent.click(screen.getByText("Vào sửa"));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("Hủy"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
