/**
 * DeleteSceneDialog tests — Task 5-4 Step 4 (BR-2 impact message, a11y default focus).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import type { SceneRow } from "@/lib/workspace-context";
import { DeleteSceneDialog } from "../DeleteSceneDialog";

const SCENE: SceneRow = {
  id: "s1",
  title: "Cảnh mở đầu",
  order: 0,
  approved: false,
  warnings: [],
  layoutClass: "Hero",
};

describe("DeleteSceneDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <DeleteSceneDialog open={false} scene={SCENE} onCancel={() => {}} onConfirm={() => {}} />,
    );
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("BR-2: states the impact before confirming", () => {
    render(
      <DeleteSceneDialog open scene={SCENE} onCancel={() => {}} onConfirm={() => {}} />,
    );
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveTextContent("Cảnh mở đầu");
    expect(dialog).toHaveTextContent("6s");
  });

  it("defaults focus to the safe (Huỷ/cancel) button", async () => {
    render(
      <DeleteSceneDialog open scene={SCENE} onCancel={() => {}} onConfirm={() => {}} />,
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Huỷ" })).toHaveFocus();
    });
  });

  it("Huỷ calls onCancel, Xoá calls onConfirm", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <DeleteSceneDialog open scene={SCENE} onCancel={onCancel} onConfirm={onConfirm} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Xoá" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Huỷ" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
